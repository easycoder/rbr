<?php
// Shared helpers for the RBR handover channel.
//
// The handover page, its endpoints and credentials.php all need the same few
// things: the host settings above the web root, the request state beside them,
// token checks against rbr-users.json, a readiness check on the proposed new
// site, and a notification email. They live here once so the page cannot grow a
// second opinion about what a valid request looks like.
//
// Nothing in this file is served directly: .htaccess leaves .php files to the
// web server, and this one returns no output.

// The host settings file sits one level above the document root and is named
// after the Host header. The Host header is validated before it is used as a
// path component, exactly as credentials.php does, so a forged host cannot walk
// out of the account.
function rbr_handover_host_settings() {
    static $cached = false;
    static $settings = array();
    if ($cached) return $settings;
    $cached = true;

    $host = isset($_SERVER['HTTP_HOST']) ? strtolower(trim($_SERVER['HTTP_HOST'])) : '';
    if (!preg_match('/^[a-z0-9.-]+$/', $host)) return $settings;

    $file = dirname(__DIR__) . '/' . $host . '.txt';
    if (!is_file($file)) return $settings;
    $data = json_decode(@file_get_contents($file), true);
    if (is_array($data)) $settings = $data;
    return $settings;
}

// The normalised handover configuration, or null when the feature is not
// configured. `handover` may be the passphrase itself (the short form) or an
// object with passphrase / owner_mac / notify / days.
function rbr_handover_config() {
    $settings = rbr_handover_host_settings();
    if (!array_key_exists('handover', $settings)) return null;

    $raw = $settings['handover'];
    if (is_string($raw)) $raw = array('passphrase' => $raw);
    if (!is_array($raw)) return null;

    $passphrase = isset($raw['passphrase']) ? trim((string)$raw['passphrase']) : '';
    if ($passphrase === '') return null;

    $days = isset($raw['days']) ? (int)$raw['days'] : 14;
    if ($days < 1 || $days > 365) $days = 14;

    // The owner MAC is what makes the PWA alert owner-only. It may sit in the
    // handover object or at the top level of the host settings.
    $owner = isset($raw['owner_mac']) ? (string)$raw['owner_mac']
        : (isset($settings['owner_mac']) ? (string)$settings['owner_mac'] : '');
    $owner = strtolower(trim($owner));
    if (!preg_match('/^[0-9a-f]{2}(:[0-9a-f]{2}){5}$/', $owner)) $owner = '';

    // Where the notification goes. An explicit `notify` wins; otherwise use
    // the address registered for the owner's own system, which is the address
    // a person actually reads; mail_from is only the sender and is a poor
    // fallback (it is usually a noreply mailbox).
    $notify = isset($raw['notify']) ? trim((string)$raw['notify']) : '';
    if ($notify === '' && $owner !== '') {
        $users = rbr_handover_load_users();
        if (isset($users[$owner]['email']) && filter_var($users[$owner]['email'], FILTER_VALIDATE_EMAIL)) {
            $notify = trim((string)$users[$owner]['email']);
        }
    }
    if ($notify === '' && isset($settings['mail_from'])) {
        $notify = trim((string)$settings['mail_from']);
    }
    $mailFrom = $notify;
    if (isset($settings['mail_from']) && trim((string)$settings['mail_from']) !== '') {
        $mailFrom = trim((string)$settings['mail_from']);
    }

    return array(
        'passphrase' => $passphrase,
        'days' => $days,
        'notify' => $notify,
        'mail_from' => $mailFrom,
        'owner_mac' => $owner,
        // Only for a local test host. Production must be https.
        'allow_http' => !empty($raw['allow_http']),
        'allow_private' => !empty($raw['allow_private']),
    );
}

// Request history and rate-limit attempts, kept outside the web root beside
// rbr-users.json. The file holds IP addresses, so it is written 0600.
function rbr_handover_state_file() {
    return dirname(__DIR__) . '/rbr-handover.json';
}

function rbr_handover_empty_state() {
    return array('requests' => array(), 'attempts' => array());
}

function rbr_handover_normalise_state($data) {
    if (!is_array($data)) return rbr_handover_empty_state();
    if (!isset($data['requests']) || !is_array($data['requests'])) $data['requests'] = array();
    if (!isset($data['attempts']) || !is_array($data['attempts'])) $data['attempts'] = array();
    return $data;
}

function rbr_handover_read_state() {
    $file = rbr_handover_state_file();
    if (!is_file($file)) return rbr_handover_empty_state();
    $handle = @fopen($file, 'r');
    if (!$handle) return rbr_handover_empty_state();
    @flock($handle, LOCK_SH);
    $raw = stream_get_contents($handle);
    @flock($handle, LOCK_UN);
    fclose($handle);
    return rbr_handover_normalise_state(json_decode($raw, true));
}

// Read-modify-write the state under one exclusive lock. $fn receives the state
// by reference and may return a value; it must not make network calls while it
// holds the lock (the callers do their readiness checks first).
function rbr_handover_mutate_state($fn) {
    $file = rbr_handover_state_file();
    $handle = @fopen($file, 'c+');
    if (!$handle) return array(false, null);
    if (!@flock($handle, LOCK_EX)) {
        fclose($handle);
        return array(false, null);
    }
    $raw = stream_get_contents($handle);
    $state = rbr_handover_normalise_state(json_decode($raw, true));
    $result = $fn($state);
    rewind($handle);
    ftruncate($handle, 0);
    fwrite($handle, json_encode($state, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_PARTIAL_OUTPUT_ON_ERROR) . "\n");
    fflush($handle);
    @chmod($file, 0600);
    @flock($handle, LOCK_UN);
    fclose($handle);
    return array(true, $result);
}

// The request that is still live: pending (countdown running) or active (the
// switch has been approved). Returns null when there is none.
function rbr_handover_current_request(&$state) {
    for ($i = count($state['requests']) - 1; $i >= 0; $i--) {
        $stateValue = isset($state['requests'][$i]['state']) ? $state['requests'][$i]['state'] : '';
        if ($stateValue === 'pending' || $stateValue === 'active') {
            return $state['requests'][$i];
        }
    }
    return null;
}

function rbr_handover_current_index(&$state) {
    for ($i = count($state['requests']) - 1; $i >= 0; $i--) {
        $stateValue = isset($state['requests'][$i]['state']) ? $state['requests'][$i]['state'] : '';
        if ($stateValue === 'pending' || $stateValue === 'active') return $i;
    }
    return -1;
}

function rbr_handover_find_index(&$state, $id) {
    for ($i = 0; $i < count($state['requests']); $i++) {
        if (isset($state['requests'][$i]['id']) && $state['requests'][$i]['id'] === $id) return $i;
    }
    return -1;
}

function rbr_handover_mac_is_valid($mac) {
    return (bool)preg_match('/^[0-9a-f]{2}(:[0-9a-f]{2}){5}$/', $mac);
}

function rbr_handover_load_users() {
    $file = dirname(__DIR__) . '/rbr-users.json';
    if (!is_file($file)) return array();
    $data = json_decode(@file_get_contents($file), true);
    return is_array($data) ? $data : array();
}

// True when the MAC and token belong to a verified system. Used by the status
// and cancel endpoints; the token is the same one credentials.php accepts.
function rbr_handover_token_is_valid($mac, $token) {
    if (!rbr_handover_mac_is_valid($mac) || $token === '') return false;
    $users = rbr_handover_load_users();
    if (!isset($users[$mac]) || !is_array($users[$mac])) return false;
    $system = $users[$mac];
    return !empty($system['verified']) && !empty($system['token'])
        && hash_equals((string)$system['token'], (string)$token);
}

// A verified system, without requiring its token. Used only to let a controller
// that has no .mqtt_token learn that an *active* handover exists; pending
// details and credentials are never returned on this path.
function rbr_handover_mac_is_known($mac) {
    if (!rbr_handover_mac_is_valid($mac)) return false;
    $users = rbr_handover_load_users();
    return isset($users[$mac]) && is_array($users[$mac]) && !empty($users[$mac]['verified']);
}

// A passphrase-derived signature for the cancellation link in the email. The
// owner can cancel without the PWA, and without putting a second secret in the
// host settings.
function rbr_handover_cancel_signature($id, $cfg) {
    return hash_hmac('sha256', 'cancel|' . $id, $cfg['passphrase']);
}

function rbr_handover_site_base() {
    $host = isset($_SERVER['HTTP_HOST']) ? strtolower(trim($_SERVER['HTTP_HOST'])) : '';
    if (!preg_match('/^[a-z0-9.-]+$/', $host)) return '';
    $https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
        || (isset($_SERVER['HTTP_X_FORWARDED_PROTO'])
            && strtolower((string)$_SERVER['HTTP_X_FORWARDED_PROTO']) === 'https')
        || (isset($_SERVER['SERVER_PORT']) && (int)$_SERVER['SERVER_PORT'] === 443);
    return ($https ? 'https' : 'http') . '://' . $host;
}

// Validate and normalise the address an installer enters. Returns
// [url, ''] on success and [null, reason] on failure. The URL is the site root;
// /heat/ and /credentials.php are appended by the controller.
function rbr_handover_normalise_url($raw, $cfg) {
    $raw = trim((string)$raw);
    if ($raw === '') return array(null, 'Enter the address of the new website.');
    if (strlen($raw) > 2000) return array(null, 'That address is too long.');
    if (preg_match('/[\x00-\x1f\x7f]/', $raw)) return array(null, 'That address contains control characters.');

    $parts = parse_url($raw);
    if (!is_array($parts) || empty($parts['scheme']) || empty($parts['host'])) {
        return array(null, 'Enter a complete address, such as https://example.com.');
    }
    $scheme = strtolower($parts['scheme']);
    if ($scheme !== 'https' && !($cfg['allow_http'] && $scheme === 'http')) {
        return array(null, 'The new website must be an https address.');
    }
    if (isset($parts['user']) || isset($parts['pass'])) {
        return array(null, 'The address must not contain a username or password.');
    }
    if (isset($parts['query']) || isset($parts['fragment'])) {
        return array(null, 'Enter the site address only, without a query or fragment.');
    }

    $host = strtolower($parts['host']);
    if (!preg_match('/^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$/', $host) || strpos($host, '..') !== false) {
        return array(null, 'That host name is not valid.');
    }

    $path = isset($parts['path']) ? $parts['path'] : '';
    $path = rtrim($path, '/');
    if ($path !== '' && (strpos($path, '..') !== false || !preg_match('#^/[A-Za-z0-9._~!$&\'()*+,;=:@%/-]*$#', $path))) {
        return array(null, 'That path is not valid.');
    }

    $url = $scheme . '://' . $host;
    if (isset($parts['port'])) {
        $port = (int)$parts['port'];
        if ($port < 1 || $port > 65535) return array(null, 'That port is not valid.');
        $url .= ':' . $port;
    }
    return array($url . $path, '');
}

// Guard against using the handover form to probe the server's own network. The
// passphrase is the real gate, but this keeps a leaked passphrase from turning
// the host into an SSRF tool.
function rbr_handover_host_is_public($url, $cfg) {
    if (!empty($cfg['allow_private'])) return true;
    $parts = parse_url($url);
    if (!is_array($parts) || empty($parts['host'])) return false;
    $host = strtolower($parts['host']);

    if (filter_var($host, FILTER_VALIDATE_IP)) {
        return filter_var($host, FILTER_VALIDATE_IP,
            FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE) !== false;
    }

    $ips = array();
    $records = @dns_get_record($host, DNS_A | DNS_AAAA);
    if (is_array($records)) {
        foreach ($records as $record) {
            if (!empty($record['ip'])) $ips[] = $record['ip'];
            if (!empty($record['ipv6'])) $ips[] = $record['ipv6'];
        }
    }
    if (!$ips) {
        $v4 = @gethostbynamel($host);
        if (is_array($v4)) $ips = $v4;
    }
    if (!$ips) return false;

    foreach ($ips as $ip) {
        if (filter_var($ip, FILTER_VALIDATE_IP,
                FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE) === false) {
            return false;
        }
    }
    return true;
}

// Minimal HTTP GET with TLS verification and no redirects. Returns
// ['status' => int, 'body' => string, 'type' => string, 'error' => string].
// A redirect is deliberately not followed: the readiness check has to reach the
// site the controller will actually use.
function rbr_handover_http_get($url, $timeout) {
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt_array($ch, array(
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => $timeout,
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_USERAGENT => 'RBR-handover/1',
            CURLOPT_HTTPHEADER => array('Accept: text/plain, application/json'),
            CURLOPT_MAXFILESIZE => 65536,
        ));
        $body = curl_exec($ch);
        $status = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $type = (string)curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
        $error = (string)curl_error($ch);
        curl_close($ch);
        if ($body === false) $body = '';
        return array(
            'status' => $status,
            'body' => substr((string)$body, 0, 65536),
            'type' => $type,
            'error' => $error,
        );
    }

    $context = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'timeout' => $timeout,
            'ignore_errors' => true,
            'follow_location' => 0,
            'max_redirects' => 1,
            'header' => "User-Agent: RBR-handover/1\r\nAccept: text/plain, application/json\r\n",
        ),
        'ssl' => array('verify_peer' => true, 'verify_peer_name' => true),
    ));
    $body = @file_get_contents($url, false, $context, 0, 65536);
    $status = 0;
    $type = '';
    if (isset($http_response_header) && is_array($http_response_header)) {
        foreach ($http_response_header as $header) {
            if (preg_match('#^HTTP/\S+\s+(\d{3})#', $header, $m)) $status = (int)$m[1];
            if (stripos($header, 'Content-Type:') === 0) $type = trim(substr($header, 13));
        }
    }
    return array(
        'status' => $status,
        'body' => $body === false ? '' : substr($body, 0, 65536),
        'type' => $type,
        'error' => $body === false ? 'request failed' : '',
    );
}

// Is the proposed site actually a prepared RBR site? Two checks, both things
// the controller itself will need on the day it switches:
//   /heat/version   must return the numeric release stamp the updater reads;
//   /credentials.php must answer 401 without a token, which proves the endpoint
//                   is there and is refusing unauthorised callers.
// Returns [true, ''] or [false, reason].
function rbr_handover_check_site($url, $cfg) {
    $normalised = rbr_handover_normalise_url($url, $cfg);
    if ($normalised[0] === null) return array(false, $normalised[1]);
    $base = $normalised[0];

    if (!rbr_handover_host_is_public($base, $cfg)) {
        return array(false, 'The address does not resolve to a public site.');
    }

    $version = rbr_handover_http_get($base . '/heat/version', 10);
    if ($version['status'] !== 200) {
        return array(false, 'The new site did not answer /heat/version (HTTP ' . $version['status'] . ').');
    }
    if (!preg_match('/^\d{8,14}$/', trim($version['body']))) {
        return array(false, 'The new site did not return an RBR version stamp at /heat/version.');
    }

    $credentials = rbr_handover_http_get($base . '/credentials.php', 10);
    if ($credentials['status'] !== 401) {
        return array(false, "The new site did not answer /credentials.php with 401 (HTTP " . $credentials['status'] . "); it is not ready to serve RBR systems.");
    }

    return array(true, '');
}

// Send the owner an email. A mail failure does not fail the request: the PWA
// alert and the stored record still exist, and the page reports that the
// request was received.
function rbr_handover_send_mail($subject, $body, $cfg) {
    if ($cfg['notify'] === '' || !filter_var($cfg['notify'], FILTER_VALIDATE_EMAIL)) return false;

    $from = $cfg['mail_from'] !== '' ? $cfg['mail_from'] : $cfg['notify'];
    if (!filter_var($from, FILTER_VALIDATE_EMAIL)) $from = $cfg['notify'];
    $subject = str_replace(array("\r", "\n"), ' ', $subject);
    $headers = array(
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'From: Room By Room <' . $from . '>',
        'Reply-To: ' . $from,
        'X-RBR-Handover: 1',
    );
    return @mail($cfg['notify'], $subject, $body, implode("\r\n", $headers));
}

function rbr_handover_utc($timestamp) {
    return gmdate('Y-m-d H:i', (int)$timestamp) . ' UTC';
}

// Request headers are stored and later written to JSON and to an email. Keep
// them printable ASCII and bounded so an exotic user agent cannot make
// json_encode fail or smuggle a header newline into the notification.
function rbr_handover_clean_text($value, $max) {
    $value = preg_replace('/[^\x20-\x7E]/', '', (string)$value);
    return substr((string)$value, 0, (int)$max);
}

function rbr_handover_requester_summary($requester) {
    $ip = isset($requester['ip']) ? $requester['ip'] : 'unknown address';
    $forwarded = isset($requester['forwarded_for']) ? $requester['forwarded_for'] : '';
    $agent = isset($requester['user_agent']) ? $requester['user_agent'] : '';
    $lines = 'Address: ' . $ip;
    if ($forwarded !== '') $lines .= "\nForwarded for: " . $forwarded;
    if ($agent !== '') $lines .= "\nBrowser: " . $agent;
    return $lines;
}

function rbr_handover_notify_request($request, $cfg) {
    $id = $request['id'];
    $base = rbr_handover_site_base();
    $cancel = $base . '/handover/?cancel=' . rawurlencode($id . '.' . rbr_handover_cancel_signature($id, $cfg));
    $body = "A handover request was submitted for Room By Room.\n\n"
        . "Requested: " . rbr_handover_utc($request['requested_at']) . "\n"
        . "Requester: " . rbr_handover_requester_summary($request['requester']) . "\n\n"
        . "New site: " . $request['url'] . "\n"
        . "Takes effect: " . rbr_handover_utc($request['effective_at']) . "\n\n"
        . "For the next " . $cfg['days'] . " days nothing changes. Every controller will then be told, on its next update check, to use the new site and the broker its credentials endpoint names. The handover fails, rather than switching, if the new site cannot satisfy the readiness check at that point.\n\n"
        . "If this was not expected, cancel it here:\n" . $cancel . "\n\n"
        . "This notice was sent to the address configured in the host settings. It contains no passphrase.\n";
    return rbr_handover_send_mail('RBR handover request ' . $id, $body, $cfg);
}

function rbr_handover_notify_cancelled($request, $cfg) {
    $body = "The handover request below was cancelled.\n\n"
        . "Requested: " . rbr_handover_utc($request['requested_at']) . "\n"
        . "Requester: " . rbr_handover_requester_summary($request['requester']) . "\n"
        . "New site: " . $request['url'] . "\n\n"
        . "Nothing will switch. Controllers continue to use the current site and broker.\n";
    return rbr_handover_send_mail('RBR handover cancelled ' . $request['id'], $body, $cfg);
}

function rbr_handover_notify_failed($request, $cfg) {
    $body = "The handover request below could not be activated because the new site did not pass the readiness check.\n\n"
        . "Requested: " . rbr_handover_utc($request['requested_at']) . "\n"
        . "Requester: " . rbr_handover_requester_summary($request['requester']) . "\n"
        . "New site: " . $request['url'] . "\n"
        . "Reason: " . (isset($request['error']) ? $request['error'] : 'unknown') . "\n\n"
        . "Nothing switched. Controllers continue to use the current site and broker. Fix the new site and submit a fresh handover request when it is ready.\n";
    return rbr_handover_send_mail('RBR handover failed ' . $request['id'], $body, $cfg);
}

// The owner-only alert credentials.php hands to the PWA. Null for any other
// system, and null when there is nothing live to report.
function rbr_handover_alert_for($mac, $cfg) {
    if (!is_array($cfg) || $cfg['owner_mac'] === '') return null;
    if (strtolower(trim($mac)) !== $cfg['owner_mac']) return null;

    $state = rbr_handover_read_state();
    $request = rbr_handover_current_request($state);
    if ($request === null) return null;

    $remaining = (int)$request['effective_at'] - time();
    return array(
        'state' => $request['state'],
        'days_left' => $remaining > 0 ? (int)ceil($remaining / 86400) : 0,
        'requested_at' => (int)$request['requested_at'],
        'effective_at' => (int)$request['effective_at'],
        'url' => $request['url'],
    );
}

// A small per-address limit: the passphrase is the secret, and this only stops
// it being guessed at speed through the public form.
function rbr_handover_attempts_recent($ip) {
    $state = rbr_handover_read_state();
    if (!isset($state['attempts'][$ip]) || !is_array($state['attempts'][$ip])) return 0;
    $cutoff = time() - 3600;
    $count = 0;
    foreach ($state['attempts'][$ip] as $stamp) {
        if ((int)$stamp > $cutoff) $count++;
    }
    return $count;
}

function rbr_handover_record_attempt($ip) {
    rbr_handover_mutate_state(function (&$state) use ($ip) {
        $cutoff = time() - 3600;
        $kept = array();
        if (isset($state['attempts'][$ip]) && is_array($state['attempts'][$ip])) {
            foreach ($state['attempts'][$ip] as $stamp) {
                if ((int)$stamp > $cutoff) $kept[] = (int)$stamp;
            }
        }
        $kept[] = time();
        $state['attempts'][$ip] = $kept;
        return true;
    });
}
