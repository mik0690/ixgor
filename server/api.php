<?php
header('Content-Type: application/json');

// Read database
$db_file = 'database.json';
if (!file_exists($db_file)) {
    http_response_code(500);
    echo json_encode(['error' => 'Database file not found']);
    exit;
}

$db_data = json_decode(file_get_contents($db_file), true);
if (!$db_data || !isset($db_data['os_list'])) {
    http_response_code(500);
    echo json_encode(['error' => 'Invalid database format']);
    exit;
}

// Get hardware specs from request (GET or POST)
$ram_mb = isset($_REQUEST['ram_mb']) ? (int)$_REQUEST['ram_mb'] : 0;
$disk_mb = isset($_REQUEST['disk_mb']) ? (int)$_REQUEST['disk_mb'] : 0;
$flags = isset($_REQUEST['flags']) ? explode(',', $_REQUEST['flags']) : []; // e.g., '32-bit'

$response = [
    'recommended' => [],
    'high_end' => []
];

// Filter OS list
foreach ($db_data['os_list'] as $os) {
    // Check if hardware meets minimum requirements
    if ($ram_mb > 0 && $ram_mb < $os['min_ram_mb']) {
        continue;
    }
    if ($disk_mb > 0 && $disk_mb < $os['min_disk_mb']) {
        continue;
    }

    // Process editions to check for incompatibility flags
    $processed_editions = [];
    foreach ($os['editions'] as $edition) {
        $is_incompatible = false;
        foreach ($edition['incompatible_flags'] as $flag) {
            if (in_array($flag, $flags)) {
                $is_incompatible = true;
                break;
            }
        }
        $edition['incompatible'] = $is_incompatible;
        $processed_editions[] = $edition;
    }
    
    $os['editions'] = $processed_editions;

    // Group into categories
    if ($os['category'] === 'recommended') {
        $response['recommended'][] = $os;
    } elseif ($os['category'] === 'high_end') {
        $response['high_end'][] = $os;
    }
}

// Output the filtered list
echo json_encode($response);
?>
