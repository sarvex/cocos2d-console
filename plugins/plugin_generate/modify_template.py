#!/usr/bin/python
# ----------------------------------------------------------------------------
# modify the runtime template for prebuilt engine
#
# Copyright 2014 (C) zhangbin
#
# License: MIT
# ----------------------------------------------------------------------------
'''
modify the runtime template for prebuilt engine
'''

import os
import sys

from MultiLanguage import MultiLanguage
from cocos import Logging

LUA_TEMPLATE_PATH = "templates/lua-template-runtime"

XCODE_LINK_CPP_LIBS = [
    "libcocos2d"
]

XCODE_LINK_LUA_LIBS = [ "libluacocos2d", "libsimulator" ]

XCODE_LINK_JS_LIBS = [ "libjscocos2d", "libsimulator" ]

class TemplateModifier(object):
    def __init__(self, engine_path, libs_path, version):
        if os.path.isabs(engine_path):
            self.engine_path = engine_path
        else:
            self.engine_path = os.path.abspath(engine_path)

        if os.path.isabs(libs_path):
            self.libs_path = libs_path
        else:
            self.libs_path = os.path.abspath(libs_path)

        self.version = version

        if getattr(sys, 'frozen', None):
            self.cur_dir = os.path.realpath(os.path.dirname(sys.executable))
        else:
            self.cur_dir = os.path.realpath(os.path.dirname(__file__))
        proj_modifier_path = os.path.join(self.cur_dir, 'proj_modifier')
        sys.path.append(proj_modifier_path)

    def modify_xcode_proj(self, proj_file_path):
        if proj_file_path.find('cpp-template') >= 0:
            language = 'cpp'
        elif proj_file_path.find('lua-template') >= 0:
            language = 'lua'
        elif proj_file_path.find('js-template') >= 0:
            language = 'js'
        else:
            Logging.warning(MultiLanguage.get_string('GEN_TEMP_UNKNOWN_LANGUAGE_FMT', proj_file_path))
            return

        import modify_pbxproj
        pbx_proj = modify_pbxproj.XcodeProject.Load(proj_file_path)

        replace_engine_strs = []
        if language == "cpp":
            targetName = "HelloCpp"
            link_libs = XCODE_LINK_CPP_LIBS
            replace_engine_strs.append("$(SRCROOT)/../cocos2d")
        elif language == "lua":
            targetName = "HelloLua"
            link_libs = XCODE_LINK_CPP_LIBS + XCODE_LINK_LUA_LIBS
            replace_engine_strs.append("$(SRCROOT)/../../cocos2d-x")
        else:
            targetName = "HelloJavascript"
            link_libs = XCODE_LINK_CPP_LIBS + XCODE_LINK_JS_LIBS
            replace_engine_strs.extend(("$(SRCROOT)/../../cocos2d-x", "../../cocos2d-x"))
        ios_target_name = f"{targetName}-mobile"
        mac_target_name = f"{targetName}-desktop"

        # remove the target dependencies
        pbx_proj.remove_proj_reference("cocos2d_libs.xcodeproj")
        if language == "js":
            pbx_proj.remove_proj_reference("cocos2d_js_bindings.xcodeproj")
            pbx_proj.remove_proj_reference("libsimulator.xcodeproj")
            pbx_proj.remove_file_by_path("../../cocos2d-x/cocos/scripting/js-bindings/script")

            common_group = pbx_proj.get_or_create_group("JS Common")
            pbx_proj.add_file_if_doesnt_exist("../../../script", common_group, tree="<group>")
        elif language == "lua":
            pbx_proj.remove_proj_reference("cocos2d_lua_bindings.xcodeproj")
            pbx_proj.remove_proj_reference("libsimulator.xcodeproj")

        # add libraries search path
        libs_path = f"/Applications/Cocos/Cocos2d-x/{self.version}/prebuilt"
        ios_template_prebuilt_path = f"{libs_path}/ios"
        pbx_proj.add_library_search_paths(ios_template_prebuilt_path, target_name=ios_target_name, recursive=False)
        mac_template_prebuilt_path = f"{libs_path}/mac"
        pbx_proj.add_library_search_paths(mac_template_prebuilt_path, target_name=mac_target_name, recursive=False)

        # add libraries for targets
        ios_lib_group = pbx_proj.get_or_create_group("ios-libs")
        mac_lib_group = pbx_proj.get_or_create_group("mac-libs")
        for lib in link_libs:
            ios_lib_name = f"{lib} iOS.a"
            mac_lib_name = f"{lib} Mac.a"
            ios_lib_path = f"{ios_template_prebuilt_path}/{ios_lib_name}"
            pbx_proj.add_file_if_doesnt_exist(ios_lib_path, ios_lib_group, tree="<group>", target=ios_target_name)

            mac_lib_path = f"{mac_template_prebuilt_path}/{mac_lib_name}"
            pbx_proj.add_file_if_doesnt_exist(mac_lib_path, mac_lib_group, tree="<group>", target=mac_target_name)

        # add studio resources to the xcode project of cpp template
        if language == "cpp":
            pbx_proj.remove_file_by_path("CloseNormal.png")
            pbx_proj.remove_file_by_path("CloseSelected.png")
            pbx_proj.remove_file_by_path("HelloWorld.png")
            pbx_proj.remove_file_by_path("Marker Felt.ttf")
            pbx_proj.remove_file_by_path("fonts")
            pbx_proj.remove_file_by_path("res")

            res_group = pbx_proj.get_or_create_group("Resources")
            pbx_proj.add_file_if_doesnt_exist("../Resources/res", res_group, tree="<group>")

        if pbx_proj.modified:
            Logging.info(MultiLanguage.get_string('GEN_TEMP_SAVE_XCODE_PROJ_FMT', proj_file_path))
            pbx_proj.save()

        with open(proj_file_path) as f:
            file_content = f.read()
        install_path = f"/Applications/Cocos/Cocos2d-x/{self.version}"
        for old_engine_path in replace_engine_strs:
            file_content = file_content.replace(old_engine_path, install_path)

        with open(proj_file_path, "w") as f:
            f.write(file_content)

    def modify_vs_proj(self, proj_file_path):
        if proj_file_path.find('cpp-template') >= 0:
            language = 'cpp'
        elif proj_file_path.find('lua-template') >= 0:
            language = 'lua'
        elif proj_file_path.find('js-template') >= 0:
            language = 'js'
        else:
            Logging.warning(MultiLanguage.get_string('GEN_TEMP_UNKNOWN_LANGUAGE_FMT', proj_file_path))
            return

        import modify_vcxproj
        vcx_proj = modify_vcxproj.VCXProject(proj_file_path)

        # remove the project references
        vcx_proj.remove_proj_reference()

        install_path = "$(COCOS_X_ROOT)\\%s\\" % self.version

        copy_libs_cmd = "if not exist \"$(OutDir)\" mkdir \"$(OutDir)\"\n" \
                            "xcopy /Y /Q \"$(EngineRoot)\\prebuilt\\win32\\*.*\" \"$(OutDir)\"\n"
        vcx_proj.set_event_command('PreLinkEvent', copy_libs_cmd, 'debug')
        vcx_proj.set_event_command('PreLinkEvent', copy_libs_cmd, 'release')

        if language == "js":
            custom_step_event = vcx_proj.get_event_command('CustomBuildStep')
            custom_step_event.replace("$(ProjectDir)..\\..\\cocos2d-x\\cocos\\scripting\\js-bindings\\script",
                                      "$(ProjectDir)..\\..\\..\\script")
            vcx_proj.set_event_command("CustomBuildStep", custom_step_event, create_new=False)

        vcx_proj.remove_predefine_macro("_DEBUG", 'debug')

        Logging.info(MultiLanguage.get_string('GEN_TEMP_SAVE_VS_PROJ_FMT', proj_file_path))
        vcx_proj.save()

        replace_strs = ["$(EngineRoot)"]
        if language == "cpp":
            replace_strs.extend(("$(ProjectDir)..\\cocos2d", "..\\cocos2d"))
        else:
            replace_strs.extend(("$(ProjectDir)..\\..\\cocos2d-x", "..\\..\\cocos2d-x"))
        # modify the Runtime.cpp
        vcx_proj_path = os.path.dirname(proj_file_path)
        cpp_path = os.path.join(vcx_proj_path, os.path.pardir, "Classes/runtime/Runtime.cpp")
        if os.path.exists(cpp_path):
            with open(cpp_path) as f:
                file_content = f.read()
            file_content = file_content.replace("#ifndef _DEBUG", "#ifndef COCOS2D_DEBUG")
            with open(cpp_path, "w") as f:
                f.write(file_content)
        with open(proj_file_path) as f:
            file_content = f.read()
        if language == "lua":
            # replace the "lua\lua;" to "lua\luajit;"
            file_content = file_content.replace("lua\\lua;", "lua\\luajit\\include;")

        file_content = file_content.replace("MultiThreadedDebugDLL", "MultiThreadedDLL")
        for str in replace_strs:
            file_content = file_content.replace(str, install_path)
        file_content = file_content.replace('%s\\' % install_path, install_path)

        file_content = file_content.replace("%scocos\\2d\\cocos2dx.props" % install_path, "cocos2dx.props")

        with open(proj_file_path, "w") as f:
            f.write(file_content)
