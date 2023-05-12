#!/usr/bin/env python
#coding=utf-8
#
# ./download-bin.py
#
# Download cocos2d-console resources from github (https://github.com/natural-law/console-binary) and extract from ZIP
#
# Helps prevent repo bloat due to large binary files since they can
# be hosted separately.
#

"""****************************************************************************
Copyright (c) 2014 cocos2d-x.org
Copyright (c) 2014 Chukong Technologies Inc.

http://www.cocos2d-x.org

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
****************************************************************************"""

import os.path,zipfile
import shutil
import sys
import traceback
import distutils
import fileinput
import json

from optparse import OptionParser
from time import time
from sys import stdout
from distutils.errors import DistutilsError
from distutils.dir_util import copy_tree, remove_tree

class UnrecognizedFormat:
    def __init__(self, prompt):
        self._prompt = prompt
    def __str__(self):
        return self._prompt

class CocosZipInstaller(object):
    def __init__(self, workpath, config_path, version_path, remote_version_key = None):
        self._workpath = workpath
        self._config_path = config_path
        self._version_path = version_path

        data = self.load_json_file(config_path)

        self._current_version = data["version"]
        self._repo_name = data["repo_name"]
        self._filename = f'{self._current_version}.zip'
        self._url = data["repo_parent"] + self._repo_name + '/archive/' + self._filename
        self._zip_file_size = int(data["zip_file_size"])
        # 'v' letter was swallowed by github, so we need to substring it from the 2nd letter
        self._extracted_folder_name = f'{self._repo_name}-{self._current_version[1:]}'

        try:
            data = self.load_json_file(version_path)
            if remote_version_key is None:
                self._remote_version = data["version"]
            else:
                self._remote_version = data[remote_version_key]
        except:
            print("==> version file doesn't exist")

    def get_input_value(self, prompt):
        ret = raw_input(prompt)
        ret.rstrip(" \t")
        return ret

    def download_file(self):
        print(f"==> Ready to download '{self._filename}' from '{self._url}'")
        import urllib2
        try:
            u = urllib2.urlopen(self._url)
        except urllib2.HTTPError as e:
            if e.code == 404:
                print(f"==> Error: Could not find the file from url: '{self._url}'")
            print(
                f"==> Http request failed, error code: {str(e.code)}, reason: {e.read()}"
            )
            sys.exit(1)

        with open(self._filename, 'wb') as f:
            meta = u.info()
            content_len = meta.getheaders("Content-Length")
            file_size = 0
            if content_len and len(content_len) > 0:
                file_size = int(content_len[0])
            else:
                        # github server may not reponse a header information which contains `Content-Length`,
                        # therefore, the size needs to be written hardcode here. While server doesn't return
                        # `Content-Length`, use it instead
                print(
                    f"==> WARNING: Couldn't grab the file size from remote, use 'zip_file_size' section in '{self._config_path}'"
                )
                file_size = self._zip_file_size

            print("==> Starting to download, please wait ...")

            file_size_dl = 0
            block_sz = 8192
            block_size_per_second = 0
            old_time=time()

            while True:
                buffer = u.read(block_sz)
                if not buffer:
                    break

                file_size_dl += len(buffer)
                block_size_per_second += len(buffer)
                f.write(buffer)
                new_time = time()
                if (new_time - old_time) > 1:
                    speed = block_size_per_second / (new_time - old_time) / 1000.0
                    status = ""
                    if file_size != 0:
                        percent = file_size_dl * 100. / file_size
                        status = r"Downloaded: %6dK / Total: %dK, Percent: %3.2f%%, Speed: %6.2f KB/S " % (file_size_dl / 1000, file_size / 1000, percent, speed)
                    else:
                        status = r"Downloaded: %6dK, Speed: %6.2f KB/S " % (file_size_dl / 1000, speed)

                    status += chr(8)*(len(status)+1)
                    print(status),
                    sys.stdout.flush()
                    block_size_per_second = 0
                    old_time = new_time

            print("==> Downloading finished!")

    def ensure_directory(self, target):
        if not os.path.exists(target):
            os.mkdir(target)

    def unpack_zipfile(self, extract_dir):
        """Unpack zip `filename` to `extract_dir`

        Raises ``UnrecognizedFormat`` if `filename` is not a zipfile (as determined
        by ``zipfile.is_zipfile()``).
        """

        if not zipfile.is_zipfile(self._filename):
            raise UnrecognizedFormat(f"{self._filename} is not a zip file")

        print("==> Extracting files, please wait ...")
        z = zipfile.ZipFile(self._filename)
        try:
            for info in z.infolist():
                name = info.filename

                # don't extract absolute paths or ones with .. in them
                if name.startswith('/') or '..' in name:
                    continue

                target = os.path.join(extract_dir, *name.split('/'))
                if not target:
                    continue
                if name.endswith('/'):
                    # directory
                    self.ensure_directory(target)
                else:
                    # file
                    data = z.read(info.filename)
                    f = open(target,'wb')
                    try:
                        f.write(data)
                    finally:
                        f.close()
                        del data
                if unix_attributes := info.external_attr >> 16:
                    os.chmod(target, unix_attributes)
        finally:
            z.close()
            print("==> Extraction done!")


    def ask_to_delete_downloaded_zip_file(self):
        ret = self.get_input_value(
            f"==> Delete '{self._filename}' file? It may be reused when you execute this script next time! (yes/no): "
        )
        ret = ret.strip()
        if ret not in ['yes', 'no']:
            print("==> Invalid answer, please answer 'yes' or 'no'!")
            return self.ask_to_delete_downloaded_zip_file()
        else:
            return ret == 'yes'

    def download_zip_file(self):
        if not os.path.isfile(self._filename):
            self.download_file()
        try:
            if not zipfile.is_zipfile(self._filename):
                raise UnrecognizedFormat(f"{self._filename} is not a zip file")
        except UnrecognizedFormat as e:
            print(f"==> Unrecognized zip format from your local '{self._filename}' file!")
            if os.path.isfile(self._filename):
                os.remove(self._filename)
            print("==> Download it from internet again, please wait...")
            self.download_zip_file()

    def need_to_update(self):
        if not os.path.isfile(self._version_path):
            return True

        with open(self._version_path) as data_file:
            data = json.load(data_file)

        return self._remote_version != self._current_version

    def load_json_file(self, file_path):
        if not os.path.isfile(file_path):
            raise Exception(f"Could not find ({file_path})")

        with open(file_path) as data_file:
            data = json.load(data_file)
        return data

    def run(self, folder_for_extracting, remove_downloaded, force_update, download_only):
        if not force_update and not self.need_to_update():
            print("==> No need to update!")
            return

        if os.path.exists(self._extracted_folder_name):
            shutil.rmtree(self._extracted_folder_name)

        self.download_zip_file()

        if not download_only:
            self.unpack_zipfile(self._workpath)
            print("==> Copying files...")
            dst_folder_path = os.path.join(self._workpath, folder_for_extracting)
            if not os.path.exists(dst_folder_path):
                os.makedirs(dst_folder_path)
            distutils.dir_util.copy_tree(self._extracted_folder_name, dst_folder_path)
            print("==> Cleaning...")
            if os.path.exists(self._extracted_folder_name):
                shutil.rmtree(self._extracted_folder_name)
            if os.path.isfile(self._filename) and (
                remove_downloaded != None
                and remove_downloaded == 'yes'
                or remove_downloaded is None
                and self.ask_to_delete_downloaded_zip_file()
            ):
                os.remove(self._filename)
        else:
            print(f"==> Download ({self._filename}) finish!")


def _check_python_version():
    major_ver = sys.version_info[0]
    if major_ver > 2:
        print ("The python version is %d.%d. But python 2.x is required. (Version 2.7 is well tested)\n"
               "Download it here: https://www.python.org/" % (major_ver, sys.version_info[1]))
        return False

    return True

def main():
    workpath = os.path.dirname(os.path.realpath(__file__))

    if not _check_python_version():
        sys.exit(1)

    parser = OptionParser()
    parser.add_option('-r', '--remove-download',
                      action="store", type="string", dest='remove_downloaded', default=None,
                      help="Whether to remove downloaded zip file, 'yes' or 'no'")

    parser.add_option("-f", "--force-update",
                      action="store_true", dest="force_update", default=False,
                      help="Whether to force update the third party libraries")

    parser.add_option("-d", "--download-only",
                      action="store_true", dest="download_only", default=False,
                      help="Only download zip file of the third party libraries, will not extract it")

    (opts, args) = parser.parse_args()

    print("=======================================================")
    print("==> Preparing to download console binaries!")
    installer = CocosZipInstaller(workpath, os.path.join(workpath, 'config.json'), os.path.join(workpath, 'version.json'), "version")
    installer.run("", opts.remove_downloaded, opts.force_update, opts.download_only)

# -------------- main --------------
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
