#!/bin/bash

set -e

rm -rf /tmp/cr-build
mkdir -p /tmp/cr-build
cd /tmp/cr-build
fetch --no-history chromium
gclient sync
cd src
git pull origin master
build/install-build-deps.sh --no-prompt
gclient runhooks
mkdir -p out/Headless
mkdir -p out/Default

echo 'import("//build/args/headless.gn")'   > out/Headless/args.gn
echo 'is_debug = false'                    >> out/Headless/args.gn
echo 'symbol_level = 0'                    >> out/Headless/args.gn
echo 'is_component_build = true'           >> out/Headless/args.gn
# echo 'remove_webcore_debug_symbols = true' >> out/Headless/args.gn
# echo 'enable_nacl = false'                 >> out/Headless/args.gn

# echo 'is_debug = false'                     > out/Default/args.gn
# echo 'symbol_level = 0'                    >> out/Default/args.gn
# echo 'remove_webcore_debug_symbols = true' >> out/Default/args.gn
# echo 'enable_nacl = false'                 >> out/Default/args.gn
gn gen out/Headless
# gn gen out/Default
ninja -C out/Headless headless
# ninja -C out/Default

