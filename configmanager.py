import json
import os


class configmanager:   
    def __init__(self, name = "config.json"):
        self.config_name = name
        self.readConfig()
        pass

    def readConfig( self ):
        try:
            config_path = os.path.join(os.path.dirname(__file__), self.config_name)
            with open(config_path, 'r', encoding='utf-8') as f:
                self.currentConfig = json.load(f)
        except FileNotFoundError:
            self.currentConfig = {}
        

    def saveConfig( self ):
        config_path = os.path.join(os.path.dirname(__file__), self.config_name)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.currentConfig, f, indent=4, ensure_ascii=False)


    def get( self, key, default=None ):
        return self.currentConfig.get(key, default)
    
    def set( self, key, value ):
        self.currentConfig[key] = value
        pass

config = configmanager()

