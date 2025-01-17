import configparser

# Tworzenie obiektu configparser
config = configparser.ConfigParser()

# Wczytywanie pliku config.ini
config.read('config.ini')

# Odczytanie opcji z sekcji 'settings'
shadowQuality = config.getint('settings', 'shadowQuality')  # Liczba całkowita
shadowQualityStep = config.getfloat('settings', 'shadowQualityStep')  # Liczba zmiennoprzecinkowa
screenWidth = config.getint('settings', 'screenWidth')  # Liczba całkowita
screenHeight = config.getint('settings', 'screenHeight')  # Liczba całkowita