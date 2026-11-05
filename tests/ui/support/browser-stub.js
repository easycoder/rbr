// browser-stub.js — the page's MQTT client, replaced by a scripted one.
//
// Installed with page.addInitScript before any page script runs, and the CDN's
// mqtt.min.js is routed to an empty body so it cannot overwrite this. The
// AllSpeak shell therefore connects to `window.mqtt` exactly as it does in
// production, but the "broker" and "controller" are the spec.
//
// Incoming controller traffic:
//   window.__rbr.pushMap(map)       a valid map (object or JSON text)
//   window.__rbr.pushRaw(payload)   exactly what a controller sent, however wrong
//   window.__rbr.emit(ev, ...args)  any client event, e.g. ('error', new Error())
//   window.__rbr.disconnect()       a closed socket
//   window.__rbr.connectAgain()     the reconnect event
//   window.__rbr.failPublish = true upstream publishes fail without arriving
//
// Outgoing UI traffic is recorded in window.__rbr.sent (also window.__sent):
//   [{ topic, payload, at }]
// which is what the specs assert against instead of page.waitForRequest —
// there is no HTTP request to watch.
//
// The MAC placeholder on the next line is replaced by the harness before the
// script is installed. A MAC is what keeps the shell out of demo mode once
// credentials.json answers.

var RBR_TEST_MAC = __RBR_TEST_MAC__;

try {
  if (RBR_TEST_MAC) window.localStorage.setItem('dev-mac', RBR_TEST_MAC);
  else window.localStorage.removeItem('dev-mac');
} catch (e) {
  /* storage blocked; the shell will fall into demo mode and the test will say so */
}

(function () {
  var sent = [];
  var client = null;

  function decodePayload(payload) {
    if (typeof payload === 'string') return payload;
    if (payload && payload.byteLength !== undefined) return new TextDecoder().decode(payload);
    if (payload && payload.buffer) return new TextDecoder().decode(new Uint8Array(payload.buffer));
    return String(payload);
  }

  // The runtime splits requests larger than one publish into chunks:
  //   !part!<index> <total> <body>   and finally   !last!<total> <body>
  // A small message is a single `!last!1`. Reassemble without separators, or a
  // JSON.parse sees a newline in the middle of a string.
  function messages() {
    var parts = [];
    var total = 0;
    var out = [];
    for (var i = 0; i < sent.length; i++) {
      var text = decodePayload(sent[i].payload);
      var m = /^!part!(\d+) (\d+) /.exec(text);
      if (m) {
        parts[Number(m[1])] = text.slice(m[0].length);
        total = Number(m[2]);
        continue;
      }
      m = /^!last!(\d+) /.exec(text);
      if (m) {
        total = Number(m[1]);
        parts[total - 1] = text.slice(m[0].length);
        out.push(parts.slice(0, total).join(''));
        parts = [];
        total = 0;
        continue;
      }
      out.push(text);
    }
    return out;
  }

  function emit(handlers, event) {
    var args = Array.prototype.slice.call(arguments, 2);
    var list = handlers[event] || [];
    for (var i = 0; i < list.length; i++) {
      try {
        list[i].apply(null, args);
      } catch (e) {
        // A handler throwing is the page's problem, not the stub's; surface it
        // as a page error instead of swallowing it.
        setTimeout(function () { throw e; }, 0);
      }
    }
  }

  var api = {
    sent: sent,
    connected: false,
    failPublish: false,
    client: null,
    messages: messages,

    pushMap: function (map) {
      var text = typeof map === 'string' ? map : JSON.stringify(map);
      emit(api._handlers, 'message', 'rbr-test/reply', text);
    },

    pushRaw: function (payload) {
      emit(api._handlers, 'message', 'rbr-test/reply', payload);
    },

    emit: function (event) {
      var args = Array.prototype.slice.call(arguments, 1);
      emit.apply(null, [api._handlers, event].concat(args));
    },

    disconnect: function () {
      api.connected = false;
      client.connected = false;
      emit(api._handlers, 'close');
      emit(api._handlers, 'offline');
    },

    connectAgain: function () {
      api.connected = true;
      client.connected = true;
      emit(api._handlers, 'connect', { sessionPresent: false });
    },

    _handlers: {},
  };

  window.__rbr = api;
  window.__sent = sent;
  window.__pushMap = api.pushMap;

  window.mqtt = {
    connect: function (url, options) {
      var handlers = api._handlers;
      client = {
        connected: false,
        on: function (event, fn) {
          (handlers[event] = handlers[event] || []).push(fn);
          return client;
        },
        once: function (event, fn) {
          var wrapped = function () {
            client.off(event, wrapped);
            return fn.apply(null, arguments);
          };
          return client.on(event, wrapped);
        },
        off: function (event, fn) {
          var list = handlers[event] || [];
          var at = list.indexOf(fn);
          if (at >= 0) list.splice(at, 1);
          return client;
        },
        subscribe: function (topic, opts, cb) {
          var done = typeof opts === 'function' ? opts : cb;
          if (done) setTimeout(function () { done(null, []); }, 0);
          return client;
        },
        unsubscribe: function (topic, cb) {
          if (cb) setTimeout(function () { cb(null); }, 0);
          return client;
        },
        publish: function (topic, payload, opts, cb) {
          sent.push({ topic: topic, payload: payload, at: Date.now() });
          var done = typeof opts === 'function' ? opts : cb;
          if (done) {
            setTimeout(function () {
              done(api.failPublish ? new Error('publish failed (test)') : null);
            }, 0);
          }
          return client;
        },
        end: function (force, opts, cb) {
          var done = typeof force === 'function' ? force
            : typeof opts === 'function' ? opts : cb;
          api.connected = false;
          client.connected = false;
          if (done) setTimeout(function () { done(); }, 0);
          return client;
        },
      };
      api.client = client;

      // The shell registers `on mqtt connect` immediately after connect()
      // returns; the tick gives it that chance before the connect event.
      setTimeout(function () {
        api.connected = true;
        client.connected = true;
        emit(handlers, 'connect', { sessionPresent: false });
      }, 20);
      return client;
    },
  };
})();
