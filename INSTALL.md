# Crowd Benefits Plugin Setup

## Setup Benefits Server

### 1) Install Docker Images

- Download docker-compose.yml file:

		wget https://github.com/aileron-split/unreal-backers-api/blob/7caac72c849e765f8647dea8c8c92f0de1e9794a/docker-compose.yml

- Alternatively, download .env file template:

		wget https://github.com/aileron-split/unreal-backers-api/blob/7caac72c849e765f8647dea8c8c92f0de1e9794a/.env-template -O .env

- Set environment variables (or update the variables in the .env file):
	- POSTGRES_PASSWORD
	- DJANGO_SUPERUSER_PASSWORD
	- HOST_ADDRESS
	- HOST_API_PORT

- Run docker-compose the usual way:
		
		docker-compose up

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

### Game Tiers Table

- Download tiers.csv file from Game Tiers page in the API Admin interface
- Import tiers.csv into Unreal using GameTiersStruct
- Load the table into the Plugin Subsystem (eg. in Game Instance BP)

### Backers Login Widget

- Place Backers Login widget anywhere in your game UI

### Using Backers Subsystem

...
