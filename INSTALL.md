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

- Run docker-compose the usual way for your hosting option, for example:

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
- Fill in the Patreon API Client form 
- Copy corresponding keys to Configuration > API Config in the Backers API Admin panel

### 3) Configure Tiers

- Patreon Tiers will auto-sync with Patreon Campaign
- Select all tiers, choose "Mirror selected to Game Tiers" action, and click "Go"
- Edit Game Tier codes and labels

### 4) Create a Game Version

- Click Add Game Version and provide a Version string to generate the version hash and corresponding RSA key pair


## Configure Unreal Engine Plugin

### Installing the Plugin

Once you acquired the plugin from the [Unreal Engine Marketplace](https://www.unrealengine.com/marketplace/en-US/product/backers-plugin) all you need to do is click the "Install to Engine" button for the plugin in your Epic Games Launcher. After download and install process is finished, you can open your Unreal Engine project and enable Backers in your Plugins Settings.

If you need more detailed instructions you can find them in the [Unreal Engine Documentation](https://docs.unrealengine.com/5.0/en-US/working-with-plugins-in-unreal-engine/#installingpluginsfromtheunrealenginemarketplace) pages. On the same documentation page you'll find the instructions on how to enable the plugin too. 

### Project Settings

Once the plugin is installed and enabled you're all set to configure it in your Project Settings.

- Go to Project Settings > Plugins > Backers Plugin section
- Configure your API URLs
- Copy Game Version string from the API Admin
- Copy Game Version Public key from the API Admin

### Backers Login Widget

- Place the Backers Login widget anywhere in your game UI

### Backers API Blueprint Nodes

- Bind an event to OnBackerCodeUpdated event dispatcher to respond to backer code changes
- Use the Backers Subsystem's variables to get the current backer login status and information

### Optionally: Import Game Tiers Table

Optionally, you can download and import Game Tiers list to display user friendly tier names, and/or use Unreal Engine built-in localization system to translate tier labels to different languages.

- Download .csv file from Game Tiers page in the API Admin interface
- Import the `GameTiersConfiguration.csv` file into Unreal using `BackersGameTiersStruct` as data table row type
- Configure the Backers Login Widget to use the imported data table

## Using the Backers Subsystem

Once the user/backer is logged into the system with their crowdfunding platform account and have been assigned a game tier, the information is available anywhere within project's blueprints via the special Backers Subsystem blueprint node.

Complete [Documentation for the Backers Subsystem](https://github.com/aileron-split/unreal-backers-api/wiki) and other related nodes can be found in the [Wiki pages](https://github.com/aileron-split/unreal-backers-api/wiki) for the repository.
