import json

class BaseDatabaseManager:
    def  __init__(self, config_json, user=None):

        self.config_json = config_json
        self._allowed_tables = None
        self.user = user
        
        with open(config_json, 'r', encoding='utf-8-sig') as file:
            self.config = json.load(file)
        
        self.data_sources = self.config["data_sources"]
    
    @property
    def available_collections(self):
        pass