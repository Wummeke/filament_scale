$(function() {
    function FilamentscaleViewModel(parameters) {
        var self = this;
		self.printerState = parameters[0]
		self.settingsViewModel = parameters[1];
		self.last_raw_weight = 0
		self.calibrate_known_weight = 0

        // TODO: Implement your plugin's view model here.
		self.printerState.filamentRemainingString = ko.observable("Loading...")

		self.onBeforeBinding = function() {
            self.filscalesettings = self.settingsViewModel.settings;
		};
				
		self.onDataUpdaterPluginMessage = function(plugin, message){
			if (plugin != "filamentscale") {
                return;
            }

			if(message.noMQTT) {
				new PNotify({
							title: 'MQTTPublish Error',
							text: 'Missing the <a href="https:\/\/plugins.octoprint.org\/plugins\/mqtt\/" target="_blank">MQTT<\/a> plugin. Please install that plugin to make MQTTPublish operational.',
							type: 'error',
							hide: false
							});
			}
			else{
				self.last_raw_weight = parseInt(message)
				weight = self.getWeight(message)
				if (Number.isNaN(weight)){
					error_message = {"tare": self.filscalesettings.plugins.filamentscale.tare(),
									"r_u": self.filscalesettings.plugins.filamentscale.reference_unit(),
									"parsed_r_u": parseInt(self.filscalesettings.plugins.filamentscale.reference_unit()),
									"message" : message,
									"known_weight": self.calibrate_known_weight,
									"spool_weight": self.filscalesettings.plugins.filamentscale.spool_weight()}
					console.log(error_message)
					self.filscalesettings.plugins.filamentscale.lastknownweight("Error")
					self.printerState.filamentRemainingString("Calibration Error")				 
				} else{
					self.filscalesettings.plugins.filamentscale.lastknownweight(weight)
					self.printerState.filamentRemainingString(self.getOutputWeight(weight))
					
					// if (self.mqtt_enabled){
						// $.ajax({
						// 	url: API_BASEURL + "plugin/filamentscale",
						// 	type: "POST",
						// 	dataType: "json",
						// 	data: JSON.stringify({
						// 		command: "publish",
						// 		measuredweight: (self.getOutputWeightToPublish(weight))
						// 	}),
						// 	contentType: "application/json; charset=UTF-8"
						// })
					// }
				}
			}

            
		};

        self.tare = function(){
			
			self.filscalesettings.plugins.filamentscale.tare(self.last_raw_weight)
			weight = self.getWeight(self.last_raw_weight)
			self.filscalesettings.plugins.filamentscale.lastknownweight(weight)
			
			self.printerState.filamentRemainingString(self.getOutputWeight(weight))
		};
		self.getWeight = function(weight){
			return Math.round((parseInt(weight) - self.filscalesettings.plugins.filamentscale.tare()) / parseInt(self.filscalesettings.plugins.filamentscale.reference_unit()))
		};
        self.getOutputWeight = function(weight){
			return (Math.max(weight - self.filscalesettings.plugins.filamentscale.spool_weight(), 0) + " gr.")
		};
		self.getOutputWeightToPublish = function(weight){
			return (Math.max(weight - self.filscalesettings.plugins.filamentscale.spool_weight(), 0))
		};
        self.calibrate = function(){
			console.log(self.filscalesettings.plugins.filamentscale.tare())
			weight = Math.round((self.last_raw_weight - self.filscalesettings.plugins.filamentscale.tare()))
			if (weight != 0 && self.calibrate_known_weight != 0){
				self.filscalesettings.plugins.filamentscale.reference_unit(weight / self.calibrate_known_weight)
				weight = self.getWeight(self.last_raw_weight)
				self.filscalesettings.plugins.filamentscale.lastknownweight(weight)
				self.printerState.filamentRemainingString(self.getOutputWeight(weight))
			} else {
				error_message = {"tare": self.filscalesettings.plugins.filamentscale.tare(),
								"r_u": self.filscalesettings.plugins.filamentscale.reference_unit(),
								"parsed_r_u": parseInt(self.filscalesettings.plugins.filamentscale.reference_unit()),
								"known_weight": self.calibrate_known_weight,
								"spool_weight": self.filscalesettings.plugins.filamentscale.spool_weight(),
								"weight": weight,
								"raw_weight":self.last_raw_weight}
				console.log(error_message)
			}
			
		};

		self.onStartup = function() {
            var element = $("#state").find(".accordion-inner [data-bind='text: stateString']");
            if (element.length) {
                var text = gettext("Filament Remaining");
				// var unit_text = gettext(" gr.");
                element.after("<br>" + text + ": <strong data-bind='text: filamentRemainingString'> </strong>");
            }
        };
	}
	
    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: FilamentscaleViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: ["printerStateViewModel", "settingsViewModel"],
        // Elements to bind to, e.g. #settings_plugin_filamentscale, #tab_plugin_filamentscale, ...
        elements: ["#settings_plugin_filamentscale"]
    });
});
