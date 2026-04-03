<?php
// Authentication endpoints for RBR Heating UI
// Routes: /verify, /register, /recover
// User data stored in a flat JSON file outside the web root.

header('Content-Type: application/json');

$usersFile = '../rbr-users.json';

// Load users or start empty
function load_users($file) {
    if (!file_exists($file)) return [];
    $data = json_decode(file_get_contents($file), true);
    return is_array($data) ? $data : [];
}

function save_users($file, $users) {
    file_put_contents($file, json_encode($users, JSON_PRETTY_PRINT), LOCK_EX);
}

// Get action from query string (set by .htaccess rewrite)
$action = isset($_GET['action']) ? $_GET['action'] : '';

// Read JSON body
$input = json_decode(file_get_contents('php://input'), true);
if (!$input) {
    http_response_code(400);
    die(json_encode(['error' => 'Invalid request']));
}

$users = load_users($usersFile);

switch ($action) {

case 'verify':
    $mac = strtolower(trim($input['mac'] ?? ''));
    $password = trim($input['password'] ?? '');

    if (!isset($users[$mac]) || $users[$mac]['password'] !== $password) {
        print json_encode(['ok' => false]);
        break;
    }

    $users[$mac]['verified'] = true;
    save_users($usersFile, $users);

    print json_encode(['ok' => true, 'controller_paired' => true]);
    break;

case 'register':
    $mac = strtolower(trim($input['mac'] ?? ''));
    $email = strtolower(trim($input['email'] ?? ''));

    if (!preg_match('/^[0-9a-f]{2}(:[0-9a-f]{2}){5}$/', $mac)) {
        print json_encode(['error' => 'Invalid controller ID format']);
        break;
    }
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        print json_encode(['error' => 'Invalid email address']);
        break;
    }

    if (isset($users[$mac]) && $users[$mac]['verified']) {
        print json_encode(['error' => 'This system is already registered. Use the login screen.']);
        break;
    }

    $password = str_pad(rand(0, 999999), 6, '0', STR_PAD_LEFT);
    $users[$mac] = [
        'email' => $email,
        'password' => $password,
        'verified' => false,
        'created' => time()
    ];
    save_users($usersFile, $users);

    print json_encode(['ok' => true, 'password' => $password]);
    break;

case 'recover':
    $mac = strtolower(trim($input['mac'] ?? ''));
    $email = strtolower(trim($input['email'] ?? ''));

    if (isset($users[$mac]) && $users[$mac]['email'] === $email && $users[$mac]['verified']) {
        $password = str_pad(rand(0, 999999), 6, '0', STR_PAD_LEFT);
        $users[$mac]['password'] = $password;
        save_users($usersFile, $users);

        print json_encode(['ok' => true, 'password' => $password]);
        break;
    }

    // No match — return success anyway to avoid revealing whether the account exists
    print json_encode(['ok' => true]);
    break;

default:
    http_response_code(400);
    print json_encode(['error' => 'Unknown action']);
    break;
}
