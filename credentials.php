<?php
// Hands out one system's broker credentials, and only to a paired device of that system.
//
// The MAC says which system is asking; the token — issued by auth.php when that system's
// password was verified — proves it. Each system has its own broker account, fenced to its own
// topics, so a leaked token reaches that system and nothing else. Mail settings belong to the
// host rather than the system, and are included because the controller reads them from here.

header('Content-Type: application/json');
// Never cache this: a browser holding the previous response keeps using the previous broker
// credentials, long after the account behind them has changed.
header('Cache-Control: no-store');

$mac = strtolower(trim($_GET['mac'] ?? ''));
$token = trim($_GET['token'] ?? '');

$usersFile = '../rbr-users.json';
$users = file_exists($usersFile) ? json_decode(file_get_contents($usersFile), true) : [];
if (!is_array($users)) $users = [];

$system = $users[$mac] ?? null;
$allowed = $mac !== '' && $token !== ''
    && is_array($system)
    && !empty($system['verified'])
    && !empty($system['token'])
    && hash_equals($system['token'], $token);

if (!$allowed || empty($system['credentials']['username'])) {
    // Says nothing about why: it must not reveal which systems exist, or whether a token was
    // merely wrong.
    http_response_code(401);
    echo json_encode(['error' => 'Unauthorised']);
    exit;
}

// The hostname is validated, so a forged Host header cannot walk out of this directory.
$host = $_SERVER['HTTP_HOST'] ?? '';
if (!preg_match('/^[a-z0-9.-]+$/i', $host)) {
    http_response_code(400);
    echo json_encode(['error' => 'Bad request']);
    exit;
}
$hostFile = '../' . $host . '.txt';
if (!file_exists($hostFile)) {
    http_response_code(404);
    echo json_encode(['error' => 'Credentials not found']);
    exit;
}

// Host-level settings, plus this system's own account.
$hostSettings = json_decode(file_get_contents($hostFile), true);
if (!is_array($hostSettings)) $hostSettings = [];

$creds = $system['credentials'];
$out = [
    'broker' => $creds['broker'] ?? ($hostSettings['broker'] ?? ''),
    'port' => $creds['port'] ?? ($hostSettings['port'] ?? 8883),
    'username' => $creds['username'],
    'password' => $creds['password'] ?? ''
];
foreach (['_doc_', 'mail_server', 'mail_login', 'mail_password', 'mail_from'] as $k) {
    if (isset($hostSettings[$k])) $out[$k] = $hostSettings[$k];
}

echo json_encode($out);
