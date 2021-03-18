# coding=utf-8
from __future__ import absolute_import
import sys

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin
from octoprint.util import RepeatedTimer
from octoprint.server import user_permission
import flask
import threading
from .hx711 import HX711
import RPi.GPIO as GPIO

class filamentscalePlugin(octoprint.plugin.StartupPlugin,
							octoprint.plugin.TemplatePlugin,
							octoprint.plugin.SettingsPlugin,
							octoprint.plugin.AssetPlugin,
							octoprint.plugin.SimpleApiPlugin,
							octoprint.plugin.ShutdownPlugin):

	def __init__(self):
		self.pd_sck = 21
		self.dout = 20
		self.byte_format = "MSB"
		self.bit_format = "MSB"
		self.update_interval = 1
		self.mqtt_enable = False
		self.mqtt_publish = None
		self.mqtt_basetopic = "octoprint/"
		self.mqtt_plugintopic = "plugin/filascale"
		self.mqtt_weightsubtopic = "weight"
		self.mqtttopic = ""

	def get_settings_defaults(self):
		return dict(
			tare = 8430152,
			reference_unit=-369,
			spool_weight=5,
			lastknownweight=0,
    		pd_sck = 21,
			dout = 20,
			byte_format = "MSB",
			bit_format = "MSB",
			interval = 10,
			mqtt_enable = False,
			mqtt_basetopic = "",
			mqtt_plugintopic = "filascale/",
			mqtt_weightsubtopic = "weight"
			
			# put your plugin's default settings here
		)

	def on_settings_save(self, data):
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		self.mqtt_enable = self._settings.get_boolean(["mqtt_enable"])
		self.update_interval = self._settings.get_int(["interval"])
		self.mqtt_basetopic = self._settings.get(["mqtt_basetopic"])
		self.mqtt_plugintopic = self._settings.get(["mqtt_plugintopic"])
		self.mqtt_weightsubtopic = self._settings.get(["mqtt_weightsubtopic"])
		self._logger.info("Received new settings")
		if self.mqtt_enable:
			self.link_mqtt()
		else:
			self._logger.info("MQTT publishing not enabled.")

	def get_template_configs(self):
		return [
			dict(type="settings", template="filamentscale_settings.jinja2", custom_bindings=True)
		]

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/filamentscale.js"],
			css=["css/filamentscale.css"],
			less=["less/filamentscale.less"]
		)                

	def on_startup(self, host, port):
		self._logger.info("Start filament scale plugin")
		self.hx = HX711(self.dout, self.pd_sck)
		self.hx.set_reading_format(self.byte_format, self.bit_format) 
		self.hx.reset()
		self._logger.info("Setup complete.")
		self.update_interval = self._settings.get_int(["interval"])
		self.mqtt_enable = self._settings.get_boolean(["mqtt_enable"])
		
		if self._settings.get(["mqtt_basetopic"]) == "":
			# self.mqtt_basetopic = self._settings.global_get(["plugins","mqtt","publish", "baseTopic"])
			self._settings.set(["mqtt_basetopic"], self._settings.global_get(["plugins","mqtt","publish", "baseTopic"]))
			self._settings.save()
			
		self.mqtt_basetopic = self._settings.get(["mqtt_basetopic"])
		self.mqtt_plugintopic = self._settings.get(["mqtt_plugintopic"])
		self.mqtt_weightsubtopic = self._settings.get(["mqtt_weightsubtopic"])
		if self.mqtt_enable:
			self._logger.info("Weight will be published to: "+self.mqtt_basetopic+self.mqtt_plugintopic+self.mqtt_weightsubtopic+" every "+str(self.update_interval)+" seconds.")
		else:
			self._logger.info("MQTT publishing not enabled.")

	def on_after_startup(self):
		self._logger.debug("Start repeat timer")
		self.timer = RepeatedTimer(self.update_interval, self.check_weight, run_first=True)
		self.timer.start()
		if self.mqtt_enable:
			self.link_mqtt()

	def check_weight(self):
		self.hx.power_up()
		self._logger.debug("Start Weighing")
		self.hx.reset()
		self._logger.debug("Reset scale...")
		v = self.hx.get_value()
		self._logger.debug("Measured value: %s" % v)
		self._plugin_manager.send_plugin_message(self._identifier, v)
		self._logger.debug("Value sent to frontend")
		self.hx.power_down()
		self._logger.debug("Weighting ended.")

	def link_mqtt(self):
		self.mqtttopic = self.mqtt_basetopic+self.mqtt_plugintopic
		helpers = self._plugin_manager.get_helpers("mqtt", "mqtt_publish", "mqtt_publish_with_timestamp")
		if helpers:
			if "mqtt_publish" in helpers:
				self.mqtt_publish = helpers["mqtt_publish"]
			try:			
				self.mqtt_publish(self.mqtttopic+"announce", "Weight will be reported every "+str(self.update_interval)+" seconds")
			except:
				self._plugin_manager.send_plugin_message(self._identifier, dict(noMQTT=True))
			
			if "mqtt_publish_with_timestamp" in helpers:
				self.mqtt_publish_with_timestamp = helpers["mqtt_publish_with_timestamp"]

	##~~ SimpleApiPlugin API

	def get_api_commands(self):
		return dict(publish=["measuredweight"])

	def on_api_command(self, command, data):
		if not user_permission.can():
			from flask import make_response
			return make_response("Insufficient rights", 403)
        
		if self.mqtt_enable:
			if command == "publish":
				mqttpayload = dict(value=data["measuredweight"])
				self._logger.debug(mqttpayload)
				try:
					self.mqtt_publish_with_timestamp(self.mqtttopic+self.mqtt_weightsubtopic, mqttpayload)
				except:
					self._plugin_manager.send_plugin_message(self._identifier, dict(noMQTT=True))
			else:
				self._logger.info("Received invalid API")

	##~~ ShutdownPlugin API

	def on_shutdown(self):
		self._logger.info("power down HX711 and cleanup GPIO.")
		self.hx.power_down()
		GPIO.cleanup()

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			filamentscale=dict(
				displayName="filamentscale Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="wummeke",
				repo="filamentscale",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/wummeke/filamentscale/archive/{target_version}.zip"
			)
		)


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Filament Scale"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
__plugin_pythoncompat__ = ">=3,<4" # only python 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = filamentscalePlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin5.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}