<?php
// Handover endpoints for RBR.
//
//   POST /handover.php?action=request   public: passphrase + new site URL
//   GET  /handover.php?action=status    controller: mac + token
//   POST /handover.php?action=cancel    owner: mac + token, or id + signature
//
// A request is recorded and the owner is notified at once, but nothing else
// happens for the configured waiting period (14 days by default). When a
// controller asks for status after that period, the new site is checked again:
// if it is ready the request becomes active and every controller is told the
// new address on its next update check; if it is not, the request fails and
// nothing switches.
//
// The state file lives one level above the web root, beside rbr-users.json.
// The passphrase is never stored in it and never echoed.

header('Content-Type: application/json');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

require_once __DIR__ . '/handover-lib.php';

function rbr_handover_reply($code, $data) {
    http_response_code($code);
    echo json_encode($data, JSON_PARTIAL_OUTPUT_ON_ERROR);
    exit;
}

function rbr_handover_input() {
    $raw = file_get_contents('php://input');
    $data = json_decode($raw, true);
    if (is_array($data)) return $data;
    return is_array($_POST) ? $_POST : array();
}

$cfg = rbr_handover_config();
if ($cfg === null) {
    rbr_handover_reply(404, array('ok' => false, 'error' => 'Handover is not configured on this site.'));
}

$action = isset($_GET['action']) ? (string)$_GET['action'] : '';
$method = isset($_SERVER['REQUEST_METHOD']) ? strtoupper($_SERVER['REQUEST_METHOD']) : 'GET';

switch ($action) {

case 'request':
    if ($method !== 'POST') rbr_handover_reply(405, array('ok' => false, 'error' => 'Use POST.'));

    $ip = isset($_SERVER['REMOTE_ADDR']) ? (string)$_SERVER['REMOTE_ADDR'] : 'unknown';
    if (rbr_handover_attempts_recent($ip) >= 10) {
        rbr_handover_reply(429, array('ok' => false, 'error' => 'Too many attempts from this address. Try again later.'));
    }

    $input = rbr_handover_input();
    $passphrase = isset($input['passphrase']) ? (string)$input['passphrase'] : '';
    $urlInput = isset($input['url']) ? (string)$input['url'] : '';

    if (!hash_equals($cfg['passphrase'], $passphrase)) {
        rbr_handover_record_attempt($ip);
        // A small constant delay makes guessing through the public form slow
        // even before the per-address limit above is reached.
        usleep(500000);
        rbr_handover_reply(403, array('ok' => false, 'error' => 'That passphrase was not accepted.'));
    }

    $state = rbr_handover_read_state();
    if (rbr_handover_current_request($state) !== null) {
        rbr_handover_reply(409, array('ok' => false, 'error' => 'A handover request is already in progress. It must be cancelled before another can be made.'));
    }

    $normalised = rbr_handover_normalise_url($urlInput, $cfg);
    if ($normalised[0] === null) {
        rbr_handover_reply(400, array('ok' => false, 'error' => $normalised[1]));
    }
    $url = $normalised[0];

    // The readiness check is deliberately made now, and again at activation:
    // submitting an address that already fails tells the installer at once,
    // rather than leaving a broken switch for the waiting period to discover.
    $ready = rbr_handover_check_site($url, $cfg);
    if (!$ready[0]) {
        rbr_handover_reply(502, array('ok' => false, 'error' => 'The new website is not ready: ' . $ready[1]));
    }

    $id = bin2hex(random_bytes(16));
    $now = time();
    $effective = $now + ($cfg['days'] * 86400);
    $requester = array(
        'ip' => $ip,
        'forwarded_for' => isset($_SERVER['HTTP_X_FORWARDED_FOR']) ? rbr_handover_clean_text($_SERVER['HTTP_X_FORWARDED_FOR'], 300) : '',
        'user_agent' => isset($_SERVER['HTTP_USER_AGENT']) ? rbr_handover_clean_text($_SERVER['HTTP_USER_AGENT'], 500) : '',
        'accepted_at' => $now,
    );
    $request = array(
        'id' => $id,
        'state' => 'pending',
        'url' => $url,
        'requested_at' => $now,
        'effective_at' => $effective,
        'requester' => $requester,
        'notified' => false,
        'verified_at' => null,
        'failed_at' => null,
        'cancelled_at' => null,
        'cancelled_by' => '',
        'error' => '',
    );

    $saved = rbr_handover_mutate_state(function (&$state) use ($id, $request) {
        if (rbr_handover_current_request($state) !== null) return 'busy';
        $state['requests'][] = $request;
        return $id;
    });
    if (!$saved[0]) {
        rbr_handover_reply(500, array('ok' => false, 'error' => 'The request could not be recorded. Contact the maintainer directly.'));
    }
    if ($saved[1] === 'busy') {
        rbr_handover_reply(409, array('ok' => false, 'error' => 'A handover request is already in progress.'));
    }

    $notified = rbr_handover_notify_request($request, $cfg);
    rbr_handover_mutate_state(function (&$state) use ($id, $notified) {
        $index = rbr_handover_find_index($state, $id);
        if ($index >= 0) $state['requests'][$index]['notified'] = $notified;
        return true;
    });

    rbr_handover_reply(200, array(
        'ok' => true,
        'id' => $id,
        'url' => $url,
        'requested_at' => $now,
        'effective_at' => $effective,
        'days' => $cfg['days'],
        'notified' => $notified,
    ));
    break;

case 'status':
    if ($method !== 'GET') rbr_handover_reply(405, array('ok' => false, 'error' => 'Use GET.'));

    $mac = isset($_GET['mac']) ? strtolower(trim((string)$_GET['mac'])) : '';
    $token = isset($_GET['token']) ? trim((string)$_GET['token']) : '';
    if (!rbr_handover_mac_is_valid($mac)) {
        rbr_handover_reply(401, array('ok' => false, 'error' => 'Unauthorised'));
    }
    $authenticated = rbr_handover_token_is_valid($mac, $token);
    if (!$authenticated && !rbr_handover_mac_is_known($mac)) {
        rbr_handover_reply(401, array('ok' => false, 'error' => 'Unauthorised'));
    }

    // Activation is checked here, on the first status request after the
    // waiting period, rather than on a timer: it is the moment the controllers
    // are asking, and the new site has to be reachable at that moment anyway.
    $state = rbr_handover_read_state();
    $index = rbr_handover_current_index($state);
    if ($index >= 0) {
        $request = $state['requests'][$index];
        if ($request['state'] === 'pending' && time() >= (int)$request['effective_at']) {
            $ready = rbr_handover_check_site($request['url'], $cfg);
            $id = $request['id'];
            $ok = $ready[0];
            $reason = $ready[1];
            $changed = array('request' => null, 'ok' => false);
            rbr_handover_mutate_state(function (&$state) use ($id, $ok, $reason, &$changed) {
                $index = rbr_handover_find_index($state, $id);
                if ($index < 0) return false;
                if ($state['requests'][$index]['state'] !== 'pending') return false;
                if ($ok) {
                    $state['requests'][$index]['state'] = 'active';
                    $state['requests'][$index]['verified_at'] = time();
                    $state['requests'][$index]['error'] = '';
                } else {
                    $state['requests'][$index]['state'] = 'failed';
                    $state['requests'][$index]['failed_at'] = time();
                    $state['requests'][$index]['error'] = $reason;
                }
                $changed['request'] = $state['requests'][$index];
                $changed['ok'] = $ok;
                return true;
            });
            if ($changed['request'] !== null) {
                if ($changed['ok']) {
                    rbr_handover_send_mail(
                        'RBR handover active ' . $id,
                        "The handover request " . $id . " is now active.\n\n"
                        . "New site: " . $changed['request']['url'] . "\n\n"
                        . "Controllers will switch on their next update check. Nothing else is required.\n",
                        $cfg
                    );
                } else {
                    rbr_handover_notify_failed($changed['request'], $cfg);
                }
            }
        }
    }

    $state = rbr_handover_read_state();
    $request = rbr_handover_current_request($state);
    if ($request === null) {
        rbr_handover_reply(200, array('ok' => true, 'handover' => null));
    }

    $remaining = (int)$request['effective_at'] - time();
    $view = array(
        'state' => $request['state'],
        'url' => $request['url'],
        'requested_at' => (int)$request['requested_at'],
        'effective_at' => (int)$request['effective_at'],
        'days_left' => $remaining > 0 ? (int)ceil($remaining / 86400) : 0,
    );
    if ($authenticated) {
        $view['requester'] = $request['requester'];
        if (isset($request['error']) && $request['error'] !== '') $view['error'] = $request['error'];
    } elseif ($request['state'] !== 'active') {
        // A caller without its token learns nothing about a pending request.
        rbr_handover_reply(200, array('ok' => true, 'handover' => null));
    } else {
        // An active handover is not a secret: its whole purpose is to be
        // followed by every controller, including one that has no token.
        unset($view['requested_at']);
        unset($view['days_left']);
    }

    rbr_handover_reply(200, array('ok' => true, 'handover' => $view));
    break;

case 'cancel':
    if ($method !== 'POST') rbr_handover_reply(405, array('ok' => false, 'error' => 'Use POST.'));

    $input = rbr_handover_input();
    $id = isset($input['id']) ? trim((string)$input['id']) : '';
    $sig = isset($input['sig']) ? trim((string)$input['sig']) : '';
    $mac = isset($input['mac']) ? strtolower(trim((string)$input['mac'])) : '';
    $token = isset($input['token']) ? trim((string)$input['token']) : '';

    $byEmailLink = false;
    $authorised = false;
    if ($id !== '' && $sig !== '') {
        $expected = rbr_handover_cancel_signature($id, $cfg);
        if (hash_equals($expected, $sig)) {
            $authorised = true;
            $byEmailLink = true;
        }
    }
    if (!$authorised && $mac !== '' && $token !== '') {
        if (rbr_handover_token_is_valid($mac, $token)
            && $cfg['owner_mac'] !== '' && $mac === $cfg['owner_mac']) {
            $authorised = true;
        }
    }
    if (!$authorised) {
        rbr_handover_reply(403, array('ok' => false, 'error' => 'That cancellation was not authorised.'));
    }

    $state = rbr_handover_read_state();
    if ($id === '') {
        $request = rbr_handover_current_request($state);
        if ($request !== null) $id = $request['id'];
    }
    $index = rbr_handover_find_index($state, $id);
    if ($index < 0) {
        rbr_handover_reply(404, array('ok' => false, 'error' => 'No such handover request.'));
    }
    $request = $state['requests'][$index];
    if ($request['state'] === 'active') {
        rbr_handover_reply(409, array('ok' => false, 'error' => 'The handover is already in effect and can no longer be cancelled.'));
    }
    if ($request['state'] !== 'pending') {
        rbr_handover_reply(409, array('ok' => false, 'error' => 'That handover request is no longer pending.'));
    }
    if (time() >= (int)$request['effective_at']) {
        rbr_handover_reply(409, array('ok' => false, 'error' => 'The waiting period has ended; the handover can no longer be cancelled here.'));
    }

    $changed = array('request' => null);
    rbr_handover_mutate_state(function (&$state) use ($id, $byEmailLink, &$changed) {
        $index = rbr_handover_find_index($state, $id);
        if ($index < 0) return false;
        if ($state['requests'][$index]['state'] !== 'pending') return false;
        if (time() >= (int)$state['requests'][$index]['effective_at']) return false;
        $state['requests'][$index]['state'] = 'cancelled';
        $state['requests'][$index]['cancelled_at'] = time();
        $state['requests'][$index]['cancelled_by'] = $byEmailLink ? 'email link' : 'app';
        $changed['request'] = $state['requests'][$index];
        return true;
    });
    if ($changed['request'] === null) {
        rbr_handover_reply(409, array('ok' => false, 'error' => 'The request could not be cancelled. It may have just taken effect.'));
    }

    rbr_handover_notify_cancelled($changed['request'], $cfg);
    rbr_handover_reply(200, array('ok' => true, 'id' => $id, 'state' => 'cancelled'));
    break;

default:
    rbr_handover_reply(400, array('ok' => false, 'error' => 'Unknown action.'));
}
