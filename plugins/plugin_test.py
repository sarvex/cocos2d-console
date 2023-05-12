#!/usr/bin/python
# ----------------------------------------------------------------------------
# cocos2d "test" plugin
#
# Author: Ricardo Quesada
# Copyright 2014 (C) Chukong Technologies
#
# License: MIT
# ----------------------------------------------------------------------------
'''
"test" plugin for cocos2d command line tool
'''

__docformat__ = 'restructuredtext'

import cocos


#
# Plugins should be a sublass of CCPlugin
#
class CCPluginTest(cocos.CCPlugin):

    @staticmethod
    def plugin_name():
        return "test"

    @staticmethod
    def brief_description():
        return "useful to test the plugin framework"

    def run(self, argv, dependencies):
        print(f"cocos2d path: {self.get_cocos2d_path()}")
        print(f"console path: {self.get_console_path()}")
        print(f"templates paths: {self.get_templates_paths()}")

        parser = cocos.Cocos2dIniParser()
        print(f"plugins path: {parser.get_plugins_path()}")

        print(f"cocos2d mode: {self.get_cocos2d_mode()}")
