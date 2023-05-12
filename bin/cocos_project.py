import os
import re
import json
import cocos
from MultiLanguage import MultiLanguage

class Project(object):
    CPP = 'cpp'
    LUA = 'lua'
    JS = 'js'

    CONFIG = '.cocos-project.json'

    KEY_PROJ_TYPE = 'project_type'
    KEY_HAS_NATIVE = 'has_native'
    KEY_CUSTOM_STEP_SCRIPT = "custom_step_script"
    KEY_ENGINE_VERSION = "engine_version"

    CUSTOM_STEP_PRE_BUILD        = "pre-build"
    CUSTOM_STEP_POST_BUILD       = "post-build"
    CUSTOM_STEP_PRE_NDK_BUILD    = "pre-ndk-build"
    CUSTOM_STEP_POST_NDK_BUILD   = "post-ndk-build"
    CUSTOM_STEP_PRE_COPY_ASSETS  = "pre-copy-assets"
    CUSTOM_STEP_POST_COPY_ASSETS = "post-copy-assets"
    CUSTOM_STEP_PRE_ANT_BUILD    = "pre-ant-build"
    CUSTOM_STEP_POST_ANT_BUILD   = "post-ant-build"

    @staticmethod
    def list_for_display():
        return [x.lower() for x in Project.language_list()]

    @staticmethod
    def language_list():
        return (Project.CPP, Project.LUA, Project.JS)

    def __init__(self, project_dir):
        # parse the config file
        self.info = self._parse_project_json(project_dir)

    def _parse_project_json(self, src_dir):
        proj_path = self._find_project_dir(src_dir)
        # config file is not found
        if proj_path is None:
            raise cocos.CCPluginError(MultiLanguage.get_string('PROJECT_CFG_NOT_FOUND_FMT',
                                      os.path.join(src_dir, Project.CONFIG)),
                                      cocos.CCPluginError.ERROR_PATH_NOT_FOUND)

        project_json = os.path.join(proj_path, Project.CONFIG)
        try:
            with open(project_json) as f:
                project_info = json.load(f)
        except Exception:
            if f is not None:
                f.close()
            raise cocos.CCPluginError(MultiLanguage.get_string('PROJECT_CFG_BROKEN_FMT',
                                      project_json),
                                      cocos.CCPluginError.ERROR_PARSE_FILE)

        if project_info is None:
            raise cocos.CCPluginError(MultiLanguage.get_string('PROJECT_CFG_PARSE_FAILED_FMT',
                                      Project.CONFIG), cocos.CCPluginError.ERROR_PARSE_FILE)

        if not project_info.has_key(Project.KEY_PROJ_TYPE):
            raise cocos.CCPluginError(MultiLanguage.get_string('PROJECT_CFG_GET_VALUE_FAILED_FMT',
                                      (Project.KEY_PROJ_TYPE, Project.CONFIG)),
                                      cocos.CCPluginError.ERROR_WRONG_CONFIG)

        lang = project_info[Project.KEY_PROJ_TYPE]
        lang = lang.lower()

        # The config is invalid
        if lang not in Project.language_list():
            raise cocos.CCPluginError(MultiLanguage.get_string('PROJECT_CFG_INVALID_LANG_FMT',
                                      (Project.KEY_PROJ_TYPE, ', '.join(Project.list_for_display()))),
                                      cocos.CCPluginError.ERROR_WRONG_CONFIG)

        # record the dir & language of the project
        self._project_dir = proj_path
        self._project_lang = lang

        # if is script project, record whether it has native or not
        self._has_native = False
        if (self._is_script_project() and project_info.has_key(Project.KEY_HAS_NATIVE)):
            self._has_native = project_info[Project.KEY_HAS_NATIVE]

        # if has custom step script, record it
        self._custom_step = None
        if (project_info.has_key(Project.KEY_CUSTOM_STEP_SCRIPT)):
            script_path = project_info[Project.KEY_CUSTOM_STEP_SCRIPT]
            if not os.path.isabs(script_path):
                script_path = os.path.join(self._project_dir, script_path)

            if os.path.isfile(script_path):
                import sys
                script_dir, script_name = os.path.split(script_path)
                sys.path.append(script_dir)
                self._custom_step = __import__(os.path.splitext(script_name)[0])
                cocos.Logging.info(MultiLanguage.get_string('PROJECT_INFO_FOUND_CUSTOM_STEP_FMT', script_path))
            else:
                cocos.Logging.warning(MultiLanguage.get_string('PROJECT_WARNING_CUSTOM_SCRIPT_NOT_FOUND_FMT',
                                      script_path))
                self._custom_step = None

        return project_info

    def invoke_custom_step_script(self, event, tp, args):
        try:
            if self._custom_step is not None:
                self._custom_step.handle_event(event, tp, args)
        except Exception as e:
            cocos.Logging.warning(MultiLanguage.get_string('PROJECT_WARNING_CUSTOM_STEP_FAILED_FMT', e))
            raise e

    def _find_project_dir(self, start_path):
        path = start_path
        while True:
            if cocos.os_is_win32():
                # windows root path, eg. c:\
                if re.match(".+:\\\\$", path):
                    break
            elif path == '/':
                break
            cfg_path = os.path.join(path, Project.CONFIG)
            if (os.path.exists(cfg_path) and os.path.isfile(cfg_path)):
                return path

            path = os.path.dirname(path)

        return None

    def get_proj_config(self, key):
        project_json = os.path.join(self._project_dir, Project.CONFIG)
        with open(project_json) as f:
            project_info = json.load(f)
        return project_info[key] if project_info.has_key(key) else None

    def write_proj_config(self, key, value):
        project_json = os.path.join(self._project_dir, Project.CONFIG)

        if os.path.isfile(project_json):
            with open(project_json) as f:
                project_info = json.load(f)
        if project_info is None:
            project_info = {}

        project_info[key] = value

        with open(project_json, "w") as outfile:
            json.dump(project_info, outfile, sort_keys = True, indent = 4)

    def get_project_dir(self):
        return self._project_dir

    def get_language(self):
        return self._project_lang

    def has_android_libs(self):
        if self._is_script_project():
            proj_android_path = os.path.join(self.get_project_dir(), "frameworks", "runtime-src", "proj.android", "libs")
        else:
            proj_android_path = os.path.join(self.get_project_dir(), "proj.android", "libs")

        return os.path.isdir(proj_android_path)

    def _is_native_support(self):
        return self._has_native

    def _is_script_project(self):
        return self._is_lua_project() or self._is_js_project()

    def _is_cpp_project(self):
        return self._project_lang == Project.CPP

    def _is_lua_project(self):
        return self._project_lang == Project.LUA

    def _is_js_project(self):
        return self._project_lang == Project.JS

class Platforms(object):
    ANDROID = 'android'
    IOS = 'ios'
    MAC = 'mac'
    WEB = 'web'
    WIN32 = 'win32'
    LINUX = 'linux'
    METRO = "metro"
    TIZEN = "tizen"

    CFG_CLASS_MAP = {
        ANDROID : "cocos_project.AndroidConfig",
        IOS : "cocos_project.iOSConfig",
        MAC : "cocos_project.MacConfig",
        WEB : "cocos_project.WebConfig",
        WIN32 : "cocos_project.Win32Config",
        LINUX : "cocos_project.LinuxConfig",
        METRO : "cocos_project.MetroConfig",
        TIZEN : "cocos_project.TizenConfig"
    }

    @staticmethod
    def list_for_display():
        return [x.lower() for x in Platforms.list()]

    @staticmethod
    def list():
        return Platforms.CFG_CLASS_MAP.keys()

    def __init__(self, project, current, proj_dir = None):
        self._project = project

        proj_info = self._project.info
        self._gen_available_platforms(proj_info, proj_dir)

        self._current = None
        if current is not None:
            current_lower = current.lower()
            if current_lower in self._available_platforms.keys():
                self._current = current_lower
            else:
                raise cocos.CCPluginError(MultiLanguage.get_string('PROJECT_INVALID_PLATFORM_FMT',
                                          (self._available_platforms.keys(), current)),
                                          cocos.CCPluginError.ERROR_WRONG_ARGS)

    def _filter_platforms(self, platforms):
        ret = []
        platforms_for_os = {
            "linux" : [ Platforms.WEB, Platforms.LINUX, Platforms.ANDROID, Platforms.TIZEN ],
            "mac" : [ Platforms.WEB, Platforms.IOS, Platforms.MAC, Platforms.ANDROID, Platforms.TIZEN ],
            "win32" : [ Platforms.WEB, Platforms.WIN32, Platforms.ANDROID,
                        Platforms.METRO, Platforms.TIZEN ]
        }
        for p in platforms:
            if cocos.os_is_linux() and p in platforms_for_os["linux"]:
                ret.append(p)
            if cocos.os_is_mac() and p in platforms_for_os["mac"]:
                ret.append(p)
            if cocos.os_is_win32() and p in platforms_for_os["win32"]:
                ret.append(p)

        return ret

    def _gen_available_platforms(self, proj_info, proj_dir):
        # generate the platform list for different projects
        if self._project._is_lua_project():
            if self._project._is_native_support():
                platform_list = [ Platforms.ANDROID, Platforms.WIN32, Platforms.IOS, Platforms.MAC, Platforms.LINUX, Platforms.TIZEN ]
            else:
                platform_list = (
                    [Platforms.ANDROID] if self._project.has_android_libs() else []
                )
        elif self._project._is_js_project():
            if self._project._is_native_support():
                platform_list = [ Platforms.ANDROID, Platforms.WIN32, Platforms.IOS, Platforms.MAC, Platforms.WEB, Platforms.LINUX, Platforms.METRO, Platforms.TIZEN ]
            elif self._project.has_android_libs():
                platform_list = [ Platforms.ANDROID, Platforms.WEB ]
            else:
                platform_list = [ Platforms.WEB ]
        elif self._project._is_cpp_project():
            platform_list = [ Platforms.ANDROID, Platforms.WIN32, Platforms.IOS, Platforms.MAC, Platforms.LINUX, Platforms.METRO, Platforms.TIZEN ]

        # filter the available platform list
        platform_list = self._filter_platforms(platform_list)

        # check the real available platforms
        self._available_platforms = {}
        root_path = self._project.get_project_dir()
        for p in platform_list:
            cfg_class = cocos.get_class(Platforms.CFG_CLASS_MAP[p])
            if cfg_class is None:
                continue

            cfg_key = f"{p}_cfg"
            if proj_info.has_key(cfg_key):
                cfg_obj = cfg_class(root_path, self._project._is_script_project(), proj_info[cfg_key])
            else:
                cfg_obj = cfg_class(root_path, self._project._is_script_project())

            if proj_dir is not None:
                cfg_obj.proj_path = os.path.join(root_path, proj_dir)

            if cfg_obj._is_available():
                self._available_platforms[p] = cfg_obj

        # don't have available platforms
        if not self._available_platforms:
            raise cocos.CCPluginError(MultiLanguage.get_string('PROJECT_NO_AVAILABLE_PLATFORMS'),
                                      cocos.CCPluginError.ERROR_WRONG_CONFIG)

    def get_current_platform(self):
        return self._current

    def get_available_platforms(self):
        return self._available_platforms

    def none_active(self):
        return self._current is None

    def is_android_active(self):
        return self._current == Platforms.ANDROID

    def is_ios_active(self):
        return self._current == Platforms.IOS

    def is_mac_active(self):
        return self._current == Platforms.MAC

    def is_web_active(self):
        return self._current == Platforms.WEB

    def is_win32_active(self):
        return self._current == Platforms.WIN32

    def is_linux_active(self):
        return self._current == Platforms.LINUX

    def is_metro_active(self):
        return self._current == Platforms.METRO

    def is_tizen_active(self):
        return self._current == Platforms.TIZEN

    def get_current_config(self):
        return None if self.none_active() else self._available_platforms[self._current]

    def project_path(self):
        if self._current is None:
            return None

        cfg_obj = self._available_platforms[self._current]
        return cfg_obj.proj_path

    def _has_one(self):
        return len(self._available_platforms) == 1

    def select_one(self):
        if self._has_one():
            self._current = self._available_platforms.keys()[0]
            return

        raise cocos.CCPluginError(MultiLanguage.get_string('PROJECT_SPECIFY_PLATFORM_FMT',
                                  str(self._available_platforms.keys())),
                                  cocos.CCPluginError.ERROR_WRONG_CONFIG)

class PlatformConfig(object):
    KEY_PROJ_PATH = "project_path"
    def __init__(self, proj_root_path, is_script, cfg_info = None):
        self._proj_root_path = proj_root_path
        self._is_script = is_script
        if cfg_info is None:
            self._use_default()
        else:
            self._parse_info(cfg_info)

    def _use_default(self):
        pass

    def _parse_info(self, cfg_info):
        if cfg_info.has_key(PlatformConfig.KEY_PROJ_PATH):
            self.proj_path = os.path.join(self._proj_root_path, cfg_info[PlatformConfig.KEY_PROJ_PATH])
        else:
            self.proj_path = None

    def _is_available(self):
        return bool(self.proj_path is not None and os.path.isdir(self.proj_path))

class AndroidConfig(PlatformConfig):

    def _use_default(self):
        if self._is_script:
            self.proj_path = os.path.join(self._proj_root_path, "frameworks", "runtime-src", "proj.android")
        else:
            self.proj_path = os.path.join(self._proj_root_path, "proj.android")

    def _parse_info(self, cfg_info):
        super(AndroidConfig, self)._parse_info(cfg_info)

    def _is_available(self):
        return super(AndroidConfig, self)._is_available()

class iOSConfig(PlatformConfig):
    KEY_PROJ_FILE = "project_file"
    KEY_TARGET_NAME = "target_name"

    def _use_default(self):
        if self._is_script:
            self.proj_path = os.path.join(self._proj_root_path, "frameworks", "runtime-src", "proj.ios_mac")
        else:
            self.proj_path = os.path.join(self._proj_root_path, "proj.ios_mac")

        self.proj_file = None
        self.target_name = None

    def _parse_info(self, cfg_info):
        super(iOSConfig, self)._parse_info(cfg_info)
        if cfg_info.has_key(iOSConfig.KEY_PROJ_FILE):
            self.proj_file = cfg_info[iOSConfig.KEY_PROJ_FILE]
        else:
            self.proj_file = None

        if cfg_info.has_key(iOSConfig.KEY_TARGET_NAME):
            self.target_name = cfg_info[iOSConfig.KEY_TARGET_NAME]
        else:
            self.target_name = None

    def _is_available(self):
        return super(iOSConfig, self)._is_available()

class MacConfig(PlatformConfig):

    def _use_default(self):
        if self._is_script:
            self.proj_path = os.path.join(self._proj_root_path, "frameworks", "runtime-src", "proj.ios_mac")
        else:
            self.proj_path = os.path.join(self._proj_root_path, "proj.ios_mac")

        self.proj_file = None
        self.target_name = None

    def _parse_info(self, cfg_info):
        super(MacConfig, self)._parse_info(cfg_info)
        if cfg_info.has_key(iOSConfig.KEY_PROJ_FILE):
            self.proj_file = cfg_info[iOSConfig.KEY_PROJ_FILE]
        else:
            self.proj_file = None

        if cfg_info.has_key(iOSConfig.KEY_TARGET_NAME):
            self.target_name = cfg_info[iOSConfig.KEY_TARGET_NAME]
        else:
            self.target_name = None

    def _is_available(self):
        return super(MacConfig, self)._is_available()

class Win32Config(PlatformConfig):
    KEY_SLN_FILE = "sln_file"
    KEY_PROJECT_NAME = "project_name"
    KEY_BUILD_CFG_PATH = "build_cfg_path"
    KEY_EXE_OUT_DIR = "exe_out_dir"

    def _use_default(self):
        if self._is_script:
            self.proj_path = os.path.join(self._proj_root_path, "frameworks", "runtime-src", "proj.win32")
        else:
            self.proj_path = os.path.join(self._proj_root_path, "proj.win32")

        self.sln_file = None
        self.project_name =None
        self.build_cfg_path = None
        self.exe_out_dir = None

    def _parse_info(self, cfg_info):
        super(Win32Config, self)._parse_info(cfg_info)
        if cfg_info.has_key(Win32Config.KEY_SLN_FILE):
            self.sln_file = cfg_info[Win32Config.KEY_SLN_FILE]
        else:
            self.sln_file = None

        if cfg_info.has_key(Win32Config.KEY_PROJECT_NAME):
            self.project_name = cfg_info[Win32Config.KEY_PROJECT_NAME]
        else:
            self.project_name = None

        if cfg_info.has_key(Win32Config.KEY_BUILD_CFG_PATH):
            self.build_cfg_path = cfg_info[Win32Config.KEY_BUILD_CFG_PATH]
        else:
            self.build_cfg_path = None

        if cfg_info.has_key(Win32Config.KEY_EXE_OUT_DIR):
            self.exe_out_dir = cfg_info[Win32Config.KEY_EXE_OUT_DIR]
        else:
            self.exe_out_dir = None

    def _is_available(self):
        return super(Win32Config, self)._is_available()

class LinuxConfig(PlatformConfig):
    KEY_CMAKE_PATH = "cmake_path"
    KEY_BUILD_DIR = "build_dir"
    KEY_PROJECT_NAME = "project_name"
    KEY_BUILD_RESULT_DIR = "build_result_dir"

    def _use_default(self):
        if self._is_script:
            self.proj_path = os.path.join(self._proj_root_path, "frameworks", "runtime-src", "proj.linux")
        else:
            self.proj_path = os.path.join(self._proj_root_path, "proj.linux")

        self.cmake_path = None
        self.build_dir = None
        self.project_name = None
        self.build_result_dir = None

    def _parse_info(self, cfg_info):
        super(LinuxConfig, self)._parse_info(cfg_info)
        if cfg_info.has_key(LinuxConfig.KEY_CMAKE_PATH):
            self.cmake_path = cfg_info[LinuxConfig.KEY_CMAKE_PATH]
        else:
            self.cmake_path = None

        if cfg_info.has_key(LinuxConfig.KEY_BUILD_DIR):
            self.build_dir = cfg_info[LinuxConfig.KEY_BUILD_DIR]
        else:
            self.build_dir = None

        if cfg_info.has_key(LinuxConfig.KEY_PROJECT_NAME):
            self.project_name = cfg_info[LinuxConfig.KEY_PROJECT_NAME]
        else:
            self.project_name = None

        if cfg_info.has_key(LinuxConfig.KEY_BUILD_RESULT_DIR):
            self.build_result_dir = cfg_info[LinuxConfig.KEY_BUILD_RESULT_DIR]
        else:
            self.build_result_dir = None

    def _is_available(self):
        return super(LinuxConfig, self)._is_available()

class WebConfig(PlatformConfig):
    KEY_SUB_URL = "sub_url"
    KEY_RUN_ROOT_DIR = "run_root_dir"
    KEY_COPY_RESOURCES = "copy_resources"

    def _use_default(self):
        self.proj_path = self._proj_root_path
        self.run_root_dir = self._proj_root_path
        self.copy_res = None
        self.sub_url = None

    def _parse_info(self, cfg_info):
        super(WebConfig, self)._parse_info(cfg_info)
        if cfg_info.has_key(WebConfig.KEY_SUB_URL):
            self.sub_url = cfg_info[WebConfig.KEY_SUB_URL]
        else:
            self.sub_url = None

        if cfg_info.has_key(WebConfig.KEY_RUN_ROOT_DIR):
            self.run_root_dir = os.path.join(self._proj_root_path, cfg_info[WebConfig.KEY_RUN_ROOT_DIR])
        else:
            self.run_root_dir = None

        if cfg_info.has_key(WebConfig.KEY_COPY_RESOURCES):
            self.copy_res = cfg_info[WebConfig.KEY_COPY_RESOURCES]
        else:
            self.copy_res = None

    def _is_available(self):
        ret = super(WebConfig, self)._is_available()

        if ret:
            index_path = os.path.join(self.proj_path, "index.html")
            ret = os.path.isfile(index_path)

        return ret

class MetroConfig(PlatformConfig):
    def _use_default(self):
        if self._is_script:
            self.proj_path = os.path.join(self._proj_root_path, "frameworks", "runtime-src", "proj.win8.1-universal")
        else:
            self.proj_path = os.path.join(self._proj_root_path, "proj.win8.1-universal")

        self.sln_file = None
        self.project_name =None

    def _parse_info(self, cfg_info):
        super(MetroConfig, self)._parse_info(cfg_info)
        if cfg_info.has_key(Win32Config.KEY_SLN_FILE):
            self.sln_file = cfg_info[Win32Config.KEY_SLN_FILE]
        else:
            self.sln_file = None

        if cfg_info.has_key(Win32Config.KEY_PROJECT_NAME):
            self.project_name = cfg_info[Win32Config.KEY_PROJECT_NAME]
        else:
            self.project_name = None

    def _is_available(self):
        return super(MetroConfig, self)._is_available()

class TizenConfig(PlatformConfig):
    def _use_default(self):
        if self._is_script:
            self.proj_path = os.path.join(self._proj_root_path, "frameworks", "runtime-src", "proj.tizen")
        else:
            self.proj_path = os.path.join(self._proj_root_path, "proj.tizen")

    def _parse_info(self, cfg_info):
        super(TizenConfig, self)._parse_info(cfg_info)

    def _is_available(self):
        return super(TizenConfig, self)._is_available()
