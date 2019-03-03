#!/bin/bash
#set -eux
#===================================================================================================
#
# Build Product
#
#===================================================================================================
#---------------------------------------------------------------------------------------------------
# env
#---------------------------------------------------------------------------------------------------
dir_script="$(dirname $0)"
cd "$(cd ${dir_script}; cd ..; pwd)" || exit 1

DIR_BASE="$(pwd)"
source "${DIR_BASE}/build/setenv"

readonly PATH_ARCHIVE="${DIR_DIST}/lambda.zip"


#---------------------------------------------------------------------------------------------------
# build
#---------------------------------------------------------------------------------------------------
echo "build" >&2
echo "-- init dist dir" >&2
if [[ -d "${DIR_DIST}" ]]; then rm -r "${DIR_DIST}"; fi
mkdir "${DIR_DIST}" >&2


echo "-- copy sources" >&2
cp -pr "${DIR_SRC}/"* "${DIR_DIST}/" >/dev/null 2>&1
if [[ $? -ne 0 ]]; then echo "build failure." >&2; exit 1; fi


echo "-- download dep" >&2
pip install -r "${DIR_BASE}/requirements.txt" -t "${DIR_DIST}/" >/dev/null 2>&1
if [[ $? -ne 0 ]]; then echo "build failure." >&2; exit 1; fi


# test
"${DIR_BASE}/build/test.sh" "${DIR_DIST}"
if [[ $? -ne 0 ]]; then echo "build failure." >&2; exit 1; fi


echo "-- packaging" >&2
cd "${DIR_DIST}"
zip -r "${PATH_ARCHIVE}" ./* >/dev/null 2>&1
if [[ $? -ne 0 ]]; then echo "build failure." >&2; exit 1; fi
if [[ ! -f "${PATH_ARCHIVE}" ]]; then echo "build failure." >&2; exit 1; fi


echo "build success." >&2
echo "${PATH_ARCHIVE}"
