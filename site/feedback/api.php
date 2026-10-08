<?php
// site/feedback/api.php: visitor notes for a plannit site (spec: the project's FEEDBACK-SPEC.md).
//   POST  JSON {text, name?, image?, view?, pin?, page, lang?, website?}  -> {ok, id}
//   GET   ?counts                                                        -> {"<image>": n, "_general": n}
// Notes are appended to STORE/feedback.jsonl, outside the web root, and are never served back: the project's
// poller (feedback-pull) reads them over ssh. STORE/hidden.txt (one id per line, written by the poller) holds
// spam and test notes, left out of the counts. publish.sh fills in STORE and DOCROOT from project.conf.
const STORE = '@STORE@';
const DOCROOT = '@DOCROOT@';
const MAX_TEXT = 2000, MAX_NAME = 80, PER_HOUR = 10;
date_default_timezone_set('Europe/Athens');   // the server runs on UTC; notes and `published` read in local time

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
function out($code, $a) { http_response_code($code); echo json_encode($a, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); exit; }
function lines($f) { return is_file($f) ? file($f, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) : []; }

if ($_SERVER['REQUEST_METHOD'] === 'GET' && isset($_GET['counts'])) {
    $hidden = array_flip(array_map('trim', lines(STORE . '/hidden.txt')));
    $n = [];
    foreach (lines(STORE . '/feedback.jsonl') as $l) {
        $r = json_decode($l, true);
        if (!$r || isset($hidden[$r['id']])) continue;
        $k = $r['image'] !== '' ? $r['image'] : '_general';
        $n[$k] = ($n[$k] ?? 0) + 1;
    }
    out(200, (object)$n);
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST') out(405, ['error' => 'POST a note, or GET ?counts']);

$raw = file_get_contents('php://input', false, null, 0, 16384);
$in = json_decode($raw, true);
if (!is_array($in)) out(400, ['error' => 'bad json']);
if (!empty($in['website'])) out(200, ['ok' => true, 'id' => '']);          // the honeypot: bots fill it, people never see it

$s = fn($k, $max) => is_string($in[$k] ?? null) ? trim(mb_substr($in[$k], 0, $max)) : '';
$text = $s('text', MAX_TEXT + 1);
if ($text === '') out(400, ['error' => 'empty note']);
if (mb_strlen($text) > MAX_TEXT) out(400, ['error' => 'note longer than ' . MAX_TEXT . ' characters']);
$image = $s('image', 120); $view = $s('view', 80); $page = $s('page', 120);
if ($image !== '' && !preg_match('/^[A-Za-z0-9_.-]+\.(jpg|jpeg|png|webp)$/', $image)) out(400, ['error' => 'bad image']);
if ($view !== '' && !preg_match('/^[A-Za-z0-9_-]+$/', $view)) out(400, ['error' => 'bad view']);
if (!preg_match('#^/[A-Za-z0-9/_.-]*$#', $page) || str_contains($page, '..')) out(400, ['error' => 'bad page']);
$pin = null;
if (isset($in['pin']) && is_array($in['pin']) && count($in['pin']) === 2
    && is_numeric($in['pin'][0]) && is_numeric($in['pin'][1])) {
    $pin = [round(max(0, min(1, (float)$in['pin'][0])), 4), round(max(0, min(1, (float)$in['pin'][1])), 4)];
}

// when the image the visitor looked at was last published (rsync keeps the build's mtimes)
$published = '';
if ($image !== '') {
    $dir = rtrim(preg_replace('#/[^/]*$#', '/', $page), '/');
    $f = realpath(DOCROOT . $dir . '/' . $image);
    if ($f && str_starts_with($f, realpath(DOCROOT) . '/')) $published = date('Y-m-d H:i', filemtime($f));
}

// rate limit per IP, kept as a salted hash, never the address itself
$who = substr(hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . '|' . STORE), 0, 16);
$rl = fopen(STORE . '/ratelimit.json', 'c+');
if (!$rl || !flock($rl, LOCK_EX)) out(500, ['error' => 'store unavailable']);
$seen = json_decode(stream_get_contents($rl) ?: '{}', true) ?: [];
$now = time();
foreach ($seen as $k => $ts) { $seen[$k] = array_values(array_filter($ts, fn($t) => $t > $now - 3600)); if (!$seen[$k]) unset($seen[$k]); }
if (count($seen[$who] ?? []) >= PER_HOUR) { flock($rl, LOCK_UN); out(429, ['error' => 'too many notes from here; try again in an hour']); }
$seen[$who][] = $now;
ftruncate($rl, 0); rewind($rl); fwrite($rl, json_encode($seen)); fflush($rl); flock($rl, LOCK_UN); fclose($rl);

$note = [
    'id' => date('Ymd-His', $now) . '-' . bin2hex(random_bytes(3)),
    'time' => date('Y-m-d H:i:s', $now),
    'page' => $page, 'image' => $image, 'view' => $view, 'pin' => $pin, 'published' => $published,
    'name' => $s('name', MAX_NAME), 'text' => $text, 'lang' => $s('lang', 5), 'from' => $who,
];
$ok = file_put_contents(STORE . '/feedback.jsonl', json_encode($note, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . "\n",
                        FILE_APPEND | LOCK_EX);
if ($ok === false) out(500, ['error' => 'could not save']);
out(200, ['ok' => true, 'id' => $note['id']]);
