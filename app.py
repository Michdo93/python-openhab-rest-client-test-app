"""
python-openhab-rest-client-test-app – Flask Backend
Läuft auf Render.com, leitet Anfragen via python-openhab-rest-client
an myopenhab.org (oder jede andere openHAB-URL) weiter.
"""

import json
import threading
import queue
import traceback
import os

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

from openhab import (
    OpenHABClient, Actions, Addons, Audio, Auth,
    ChannelTypes, ConfigDescriptions, Discovery, Events,
    ItemEvents, ThingEvents, InboxEvents, LinkEvents, ChannelEvents,
    Iconsets, Inbox, Items, Links, Logging, ModuleTypes,
    Persistence, ProfileTypes, Rules, Services, Sitemaps,
    Systeminfo, Tags, Templates, ThingTypes, Things,
    Transformations, UI, UUID, Voice,
)
from openhab.tests import (
    ActionsTest, AddonsTest, AudioTest, AuthTest,
    ChannelTypesTest, ConfigDescriptionsTest, DiscoveryTest,
    IconsetsTest, InboxTest, ItemsTest, LinksTest, LoggingTest,
    ModuleTypesTest, PersistenceTest, ProfileTypesTest, RulesTest,
    ServicesTest, SitemapsTest, SysteminfoTest, TagsTest, TemplatesTest,
    ThingTypesTest, ThingsTest, TransformationsTest, UITest, UUIDTest, VoiceTest,
)

app = Flask(__name__)

# CORS: GitHub Pages Domain + lokale Entwicklung erlauben
CORS(app, origins=[
    "https://michdo93.github.io",
    "http://localhost",
    "http://127.0.0.1",
    "null",  # file:// beim lokalen Öffnen von index.html
])

# ── Session-basierter Client-Store ───────────────────────────────────────────
# Render.com ist stateless – Client-Objekte leben nur im RAM dieser Instanz.
# Für die Demo reicht ein einzelner globaler Client.
_client: OpenHABClient | None = None


def get_client() -> OpenHABClient:
    if _client is None:
        raise RuntimeError("Nicht verbunden. Bitte zuerst /api/connect aufrufen.")
    return _client


# ── Klassen-Map ──────────────────────────────────────────────────────────────
CLASS_MAP = {
    "Actions":            (Actions,            ActionsTest),
    "Addons":             (Addons,             AddonsTest),
    "Audio":              (Audio,              AudioTest),
    "Auth":               (Auth,               AuthTest),
    "ChannelTypes":       (ChannelTypes,       ChannelTypesTest),
    "ConfigDescriptions": (ConfigDescriptions, ConfigDescriptionsTest),
    "Discovery":          (Discovery,          DiscoveryTest),
    "Iconsets":           (Iconsets,           IconsetsTest),
    "Inbox":              (Inbox,              InboxTest),
    "Items":              (Items,              ItemsTest),
    "Links":              (Links,              LinksTest),
    "Logging":            (Logging,            LoggingTest),
    "ModuleTypes":        (ModuleTypes,        ModuleTypesTest),
    "Persistence":        (Persistence,        PersistenceTest),
    "ProfileTypes":       (ProfileTypes,       ProfileTypesTest),
    "Rules":              (Rules,              RulesTest),
    "Services":           (Services,           ServicesTest),
    "Sitemaps":           (Sitemaps,           SitemapsTest),
    "Systeminfo":         (Systeminfo,         SysteminfoTest),
    "Tags":               (Tags,               TagsTest),
    "Templates":          (Templates,          TemplatesTest),
    "ThingTypes":         (ThingTypes,         ThingTypesTest),
    "Things":             (Things,             ThingsTest),
    "Transformations":    (Transformations,    TransformationsTest),
    "UI":                 (UI,                 UITest),
    "UUID":               (UUID,               UUIDTest),
    "Voice":              (Voice,              VoiceTest),
}


# ── /api/connect ─────────────────────────────────────────────────────────────
@app.route("/api/connect", methods=["POST"])
def connect():
    global _client
    body     = request.get_json(force=True)
    url      = body.get("url", "").rstrip("/")
    username = body.get("username") or None
    password = body.get("password") or None
    token    = body.get("token") or None

    if not url:
        return jsonify({"error": "URL fehlt"}), 400

    try:
        _client = OpenHABClient(url=url, username=username, password=password, token=token)
        uid = UUID(_client).getUUID()
        return jsonify({"status": "ok", "uuid": uid})
    except Exception as e:
        _client = None
        return jsonify({"error": str(e)}), 500


# ── /api/classes ─────────────────────────────────────────────────────────────
@app.route("/api/classes", methods=["GET"])
def list_classes():
    result = {}
    for cls_name, (ApiClass, TestClass) in CLASS_MAP.items():
        result[cls_name] = {
            "methods":     [m for m in dir(ApiClass)  if not m.startswith("_")],
            "testMethods": [m for m in dir(TestClass) if not m.startswith("_")],
        }
    return jsonify(result)


# ── /api/call ────────────────────────────────────────────────────────────────
@app.route("/api/call", methods=["POST"])
def call_method():
    body     = request.get_json(force=True)
    cls_name = body.get("class", "")
    method   = body.get("method", "")
    args     = body.get("args", [])
    kwargs   = body.get("kwargs", {})

    if cls_name not in CLASS_MAP:
        return jsonify({"error": f"Unbekannte Klasse: {cls_name}"}), 400

    try:
        ApiClass, _ = CLASS_MAP[cls_name]
        instance = ApiClass(get_client())
        result = getattr(instance, method)(*args, **kwargs)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ── /api/test ─────────────────────────────────────────────────────────────────
@app.route("/api/test", methods=["POST"])
def run_test():
    body     = request.get_json(force=True)
    cls_name = body.get("class", "")
    method   = body.get("method", "")
    args     = body.get("args", [])
    kwargs   = body.get("kwargs", {})

    if cls_name not in CLASS_MAP:
        return jsonify({"error": f"Unbekannte Klasse: {cls_name}"}), 400

    try:
        _, TestClass = CLASS_MAP[cls_name]
        instance = TestClass(get_client())
        result = getattr(instance, method)(*args, **kwargs)
        return jsonify({"result": result, "status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ── /api/sse ──────────────────────────────────────────────────────────────────
@app.route("/api/sse", methods=["GET"])
def sse_stream():
    sse_type   = request.args.get("type", "ItemEvents")
    sse_method = request.args.get("method", "ItemStateChangedEvent")
    try:
        args = json.loads(request.args.get("args", "[]"))
    except Exception:
        args = []

    EVENT_CLASS_MAP = {
        "Events":        Events,
        "ItemEvents":    ItemEvents,
        "ThingEvents":   ThingEvents,
        "InboxEvents":   InboxEvents,
        "LinkEvents":    LinkEvents,
        "ChannelEvents": ChannelEvents,
    }

    if sse_type not in EVENT_CLASS_MAP:
        return jsonify({"error": f"Unbekannter SSE-Typ: {sse_type}"}), 400

    q: queue.Queue = queue.Queue()

    def producer():
        try:
            instance = EVENT_CLASS_MAP[sse_type](get_client())
            response = getattr(instance, sse_method)(*args)
            with response as r:
                for line in r.iter_lines():
                    decoded = line.decode("utf-8") if isinstance(line, bytes) else line
                    if decoded:
                        q.put(decoded)
        except Exception as e:
            q.put(f'data: {{"error": "{e}"}}')
        finally:
            q.put(None)

    threading.Thread(target=producer, daemon=True).start()

    def generate():
        while True:
            item = q.get()
            if item is None:
                break
            yield f"{item}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Health-Check für Render ───────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "python-openhab-rest-client backend running"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
