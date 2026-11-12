#!/usr/bin/env bash
# Test the w3id.org .htaccess against the expected redirects in apache/tests/redirects.tsv.
#
# Usage:
#   apache/test-redirects.sh                 run the .htaccess in a local Apache (Docker httpd:2.4)
#   apache/test-redirects.sh --url URL       test a running server instead, e.g. --url https://w3id.org/ontostart
#   apache/test-redirects.sh --targets       also check that every expected GitHub Pages target exists
#
# Options:
#   --htaccess PATH   .htaccess to test   (default: apache/web/ontostart/.htaccess)
#   --folder NAME     w3id folder name    (default: the .htaccess's parent directory name)
#   --table PATH      expected redirects  (default: apache/tests/redirects.tsv)
#   --port N          local port          (default: 8089)
set -uo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
htaccess="$here/web/ontostart/.htaccess"
table="$here/tests/redirects.tsv"
folder=""
url=""
port=8089
targets=0

while [ $# -gt 0 ]; do
  case "$1" in
    --htaccess) htaccess="$2"; shift 2 ;;
    --folder)   folder="$2"; shift 2 ;;
    --table)    table="$2"; shift 2 ;;
    --url)      url="${2%/}"; shift 2 ;;
    --port)     port="$2"; shift 2 ;;
    --targets)  targets=1; shift ;;
    -h|--help)  sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

[ -f "$htaccess" ] || { echo "no .htaccess at $htaccess" >&2; exit 2; }
[ -f "$table" ]    || { echo "no test table at $table" >&2; exit 2; }
htaccess="$(cd "$(dirname "$htaccess")" && pwd)/$(basename "$htaccess")"
[ -n "$folder" ] || folder="$(basename "$(dirname "$htaccess")")"

param() { sed -n "s/^RewriteRule \^ - \[E=$1:\([^]]*\)\]$/\1/p" "$htaccess" | head -1; }
pages="https://$(param GH_USER).github.io/$(param GH_REPONAME)"

container=""
cleanup() { [ -n "$container" ] && docker rm -f "$container" >/dev/null 2>&1; }
trap cleanup EXIT

if [ -z "$url" ]; then
  # Serve the .htaccess's directory at /<folder>/, as w3id.org does
  container="ontostart-htaccess-test-$$"
  docker run -d --name "$container" -p "127.0.0.1:$port:80" \
    -v "$(dirname "$htaccess"):/usr/local/apache2/htdocs/$folder:ro" \
    -v "$here/apache.conf:/usr/local/apache2/conf/extra/httpd-local.conf:ro" \
    httpd:2.4 sh -c '
      sed -i -E "s/^#\s*(LoadModule (rewrite|headers)_module)/\1/" /usr/local/apache2/conf/httpd.conf
      echo "Include conf/extra/httpd-local.conf" >> /usr/local/apache2/conf/httpd.conf
      exec httpd-foreground' >/dev/null || exit 2
  url="http://localhost:$port/$folder"
  for _ in $(seq 1 30); do
    curl -s -o /dev/null "http://localhost:$port/" && break
    sleep 0.5
  done
fi

echo "Testing $url  (pages: $pages)"
pass=0; fail=0; checked=""

while IFS=$'\t' read -r accept path expected check; do
  case "$accept" in ''|'#'*) continue ;; esac
  expected="${expected//\{pages\}/$pages}"
  expected="${expected//\{base\}/$url}"
  case "$expected" in "$url"*) want_code=301 ;; *) want_code=303 ;; esac

  got="$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' -H "Accept: $accept" "$url$path")"
  if [ "$got" = "$want_code $expected" ]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    printf 'FAIL  %s  [%s]\n      want: %s %s\n      got:  %s\n' "$path" "$accept" "$want_code" "$expected" "$got"
  fi
  if [ "$check" = "y" ]; then checked="$checked$expected"$'\n'; fi
done < "$table"

# Headers every redirect must carry
headers="$(curl -s -o /dev/null -D - -H 'Accept: text/turtle' "$url/")"
for h in 'Vary: .*Accept' 'Access-Control-Allow-Origin: \*'; do
  if printf '%s' "$headers" | grep -qiE "^$h"; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1)); echo "FAIL  header missing on redirect: $h"
  fi
done

if [ "$targets" = 1 ]; then
  echo "Checking that targets exist on $pages"
  while IFS= read -r t; do
    [ -n "$t" ] || continue
    code="$(curl -s -o /dev/null -w '%{http_code}' "$t")"
    if [ "$code" = 200 ]; then
      pass=$((pass + 1))
    else
      fail=$((fail + 1)); echo "FAIL  target $t -> $code"
    fi
  done <<< "$(printf '%s' "$checked" | sort -u)"
fi

echo "$pass passed, $fail failed"
[ "$fail" = 0 ]
