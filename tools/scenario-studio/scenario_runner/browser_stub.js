// The page's MQTT client, replaced by a scripted one.
//
// This is the Python runner's copy of the stub used by tests/ui, extended with
// protocol-level replies: a `refresh` poll is answered with an empty heartbeat
// (or the current map), so advancing the virtual clock for hours does not trip
// the shell's 60-second staleness reload. Controller *semantics* stay out of it —
// those are scenario steps.
//
// The runner passes the MAC in place of __RBR_TEST_MAC__.

var RBR_TEST_MAC = __RBR_TEST_MAC__;

try {
  if (RBR_TEST_MAC) window.localStorage.setItem('dev-mac', RBR_TEST_MAC);
  else window.localStorage.removeItem('dev-mac');
} catch (e) {
  /* storage blocked; the shell will fall into demo mode and the run will say so */
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
    autoReplyRefresh: true,
    refreshReply: 'empty',
    currentMap: null,
    _handlers: {},

    pushMap: function (map) {
      var text = typeof map === 'string' ? map : JSON.stringify(map);
      api.currentMap = text;
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
      if (client) client.connected = false;
      emit(api._handlers, 'close');
      emit(api._handlers, 'offline');
    },

    connectAgain: function () {
      api.connected = true;
      if (client) client.connected = true;
      emit(api._handlers, 'connect', { sessionPresent: false });
    },
  };

  window.__rbr = api;
  window.__sent = sent;
  window.__pushMap = api.pushMap;

  // Protocol reply, not controller logic: the real controller answers every
  // refresh with a heartbeat so the UI knows the round trip is alive.
  function autoReply(payload) {
    if (!api.autoReplyRefresh || api.refreshReply === 'none') return;
    var text = decodePayload(payload);
    text = text.replace(/^!last!\d+\s/, '').replace(/^!part!\d+\s+\d+\s/, '');
    var outer;
    try { outer = JSON.parse(text); } catch (e) { return; }
    if (!outer || outer.action !== 'refresh') return;
    var body = api.refreshReply === 'full' ? (api.currentMap || '') : '';
    setTimeout(function () {
      emit(api._handlers, 'message', 'rbr-test/reply', body);
    }, 0);
  }

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
          autoReply(payload);
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

      setTimeout(function () {
        api.connected = true;
        client.connected = true;
        emit(handlers, 'connect', { sessionPresent: false });
      }, 20);
      return client;
    },
  };
})();
