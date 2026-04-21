/**
 * Wrap the browser's MQTT client so outgoing UI boost requests have their
 * duration rewritten before publication. This lets a test exercise the full
 * round-trip (click boost button → controller → expire → revert) in seconds
 * instead of the 30-min UI minimum.
 *
 * Install BEFORE page.goto() so the init script runs before AllSpeak loads.
 *
 * Payloads in the RBR UI are chunked with a `!last!1 ` or `!part!i N ` header.
 * This interceptor only touches single-chunk (`!last!1 `) publishes, which is
 * all the mode-dialog request ever produces.
 */
async function installBoostInterceptor(page, substituteMinutes = 1) {
    await page.addInitScript((mins) => {
        const rewriteIfBoost = (uint8) => {
            try {
                const text = new TextDecoder().decode(uint8);
                // Header is `!last!<N> ` or `!part!<i> <N> `. Only intercept
                // single-chunk sends (the mode dialog payload is ~200 bytes).
                const m = text.match(/^!last!1 /);
                if (!m) return null;
                const header = m[0];
                const outer = JSON.parse(text.slice(header.length));
                // AllSpeak may pass `message` as a JSON string OR as a nested
                // object — handle both.
                const messageWasString = typeof outer.message === 'string';
                let inner = messageWasString ? JSON.parse(outer.message) : outer.message;
                if (!inner || typeof inner !== 'object') return null;
                if (inner.Action !== 'Operating Mode') return null;
                if (typeof inner.boost !== 'string' || !/^B\d+$/.test(inner.boost)) return null;
                console.log('[mqtt-intercept] rewrite', inner.boost, '->', 'B' + mins);
                inner.boost = 'B' + mins;
                outer.message = messageWasString ? JSON.stringify(inner) : inner;
                return new TextEncoder().encode(header + JSON.stringify(outer));
            } catch (e) {
                console.log('[mqtt-intercept] parse error:', e && e.message);
                return null;
            }
        };

        const wrapClient = (client) => {
            if (!client || client.__rbrBoostWrapped) return client;
            client.__rbrBoostWrapped = true;
            console.log('[mqtt-intercept] wrapping client, publish type:', typeof client.publish);
            const origPublish = client.publish.bind(client);
            client.publish = function (topic, payload, options, cb) {
                console.log('[mqtt-intercept] publish: topic=' + topic + ', payloadType=' + (payload && payload.constructor && payload.constructor.name));
                let bytes = null;
                if (payload instanceof Uint8Array) bytes = payload;
                else if (payload && payload.buffer instanceof ArrayBuffer) bytes = new Uint8Array(payload.buffer, payload.byteOffset || 0, payload.byteLength);
                else if (typeof payload === 'string') bytes = new TextEncoder().encode(payload);
                if (bytes) {
                    try {
                        const text = new TextDecoder().decode(bytes);
                        if (text.indexOf('Operating Mode') !== -1) {
                            console.log('[mqtt-intercept] saw Operating Mode publish, len=' + bytes.length + ', head=' + text.slice(0, 80));
                        }
                    } catch (_) {}
                    const rewritten = rewriteIfBoost(bytes);
                    if (rewritten) payload = rewritten;
                }
                return origPublish(topic, payload, options, cb);
            };
            return client;
        };

        const install = () => {
            if (window.mqtt && typeof window.mqtt.connect === 'function' && !window.mqtt.__rbrWrapped) {
                const origConnect = window.mqtt.connect.bind(window.mqtt);
                window.mqtt.connect = (...args) => wrapClient(origConnect(...args));
                window.mqtt.__rbrWrapped = true;
                console.log('[mqtt-intercept] installed, sub =', 'B' + mins);
                return;
            }
            setTimeout(install, 20);
        };
        install();
    }, substituteMinutes);
}

module.exports = { installBoostInterceptor };
