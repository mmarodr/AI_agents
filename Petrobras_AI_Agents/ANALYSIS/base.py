import json

class BaseDatabaseManager:
    def  __init__(self, config_json, user=None):

        self.config_json = config_json
                
        with open(config_json, 'r', encoding='utf-8-sig') as file:
            self.config = json.load(file)
        
        self.data_sources = self.config["data_sources"]