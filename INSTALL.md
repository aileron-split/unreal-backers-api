# Backers Plugin Setup

## Setup Backers API Server

### 1) Install Docker Images

- Download docker-compose.yml file:

      wget https://raw.githubusercontent.com/aileron-split/unreal-backers-api/main/docker-compose.yml -O docker-compose.yml

- Alternatively, download .env file template:

      wget https://raw.githubusercontent.com/aileron-split/unreal-backers-api/main/.env-template -O .env

- Set environment variables (or update the variables in the .env file):
	
      POSTGRES_PASSWORD=
      DJANGO_SUPERUSER_EMAIL=
      DJANGO_SUPERUSER_PASSWORD=
      ALLOWED_HOSTS=
      CSRF_TRUSTED_ORIGINS=
      HOST_API_PORT=

- Run docker-compose the usual way, for example:

      docker-compose pull
      docker-compose up -d

- Note: Here is a list of paths which need to be exposed through proxy:

      code
      register
      unregister
      admin/
      config/
      patreon/


### 2) Configure Patreon Keys

Create Patreon API Key at https://www.patreon.com/portal/registration/register-clients

- Click Create Client
- Copy corresponding keys to Configuration > API Config in the Backers API Admin panel

### 3) Configure Tiers

- Patreon Tiers will auto-sync with Patreon Campaign
- Select all tiers, choose "Mirror selected to Game Tiers" action, and click "Go"
- Edit Game Tier codes and labels

### 4) Configure Version

- Create a version to generate version hash and key pair


## Configure Unreal Engine Plugin

### Project Settings

- Go to Project Settings > Plugins > Backers Plugin section
- Configure your API URLs
- Copy Game Version string from the API Admin
- Copy Game Version Public key from the API Admin

### Backers Login Widget

- Place Backers Login widget anywhere in your game UI

### Optionally: Import Game Tiers Table

Optionally, you can download and import Game Tiers to 

- Download .csv file from Game Tiers page in the API Admin interface
- Import the `GameTiersConfiguration.csv` file into Unreal using `BackersGameTiersStruct` as data table row type

### Using Backers Subsystem

...
