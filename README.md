# Minecraft Timeline Switcher

This is a program that allows you to automatically switch minecraft versions (and optionally mods)
for both clients and the server at specific intervals/times using
[packwiz](https://packwiz.infra.link) and [Portainer](https://www.portainer.io/).

By default, it is set up to switch from Minecraft 1.0 to 1.1 and then to 1.2.5 ...,
up to the latest version one step at a time every night.
This way you can simulate the history of minecraft and see how it has changed each update.

But you can also configure it to switch between other versions and even add mods to each individual version.
However, do keep in mind that downgrades might not work due to changes in the Minecraft save format.

The name was inspired by the awesome [Minecraft Timeline](https://minecraft-timeline.github.io/) graph which I highly
recommend checking out.

## Setup

To set it up please see the options inside the config file.
The `config.toml.example` file must be copied/renamed to `config.toml`.

### Clients

If you are just switching between vanilla versions players can use the normal Minecraft Launcher to switch versions
themselves or players can automate it:

To automatically switch versions and install mods: create a MultiMC / Prism Launcher instance by following the
[packwiz-installer instructions](https://packwiz.infra.link/tutorials/installing/packwiz-installer/).
A webserver is needed to host the pack files. Therefore, a directory inside the web root needs to be accessible
by this program, for example by hosting a web server on the same host or by mounting the directory remotely.

Players should keep in mind that by using packwiz-installer they are trusting the pack author/server-admin
to not include something malicious.

### Server

In order to automatically switch the server you will need a [Portainer](https://www.portainer.io/) instance and a/an:

- Valid https address to that instance
- Existing stack to overwrite
- Portainer API key (preferably of a new user)

The server will be deployed using the `docker-compose-template.yml` file, change it to your liking, do not rename it.
You will also need to accept the minecraft EULA there in order to start the server.

Using docker-compose to instead deploy the server on the same host might happen in the future.

## Security

Before running older versions of minecraft (or any software) please be aware that some older versions might be impacted
by security vulnerabilities.

In the case of the [Log4Shell](https://en.wikipedia.org/wiki/Log4Shell)
exploit minecraft versions 1.7 to inclusive 1.18.0 are impacted, please see the
[official Minecraft article](https://www.minecraft.net/en-us/article/important-message--security-vulnerability-java-edition)
about it.

The official Minecraft Launcher, MultiMC, Prism Launcher and other "big launchers"
should all have mitigations against Log4Shell in place by now.

The default server image [itzg/docker-minecraft-server](https://github.com/itzg/docker-minecraft-server)
already had certain patches in place for vanilla and [Purpur](https://purpurmc.org/) servers.
Additionally, some server types like Bukkit and Paper have patched the last minor version of every major release
starting from 1.8, so for example 1.17.1 has been patched but 1.17(.0) was not.

This meant that some odd versions like Paper 1.16.4, 1.17(.0), but also Bukkit 1.7.10 were still vulnerable!

Since **2023-05-28** the [CreeperHost/Log4jPatcher](https://github.com/CreeperHost/Log4jPatcher) is being used in
[itzg/docker-minecraft-server](https://github.com/itzg/docker-minecraft-server)
which should patch all affected versions, including the ones stated above.
See the [issue](https://github.com/itzg/docker-minecraft-server/issues/2101) and
[pull request](https://github.com/itzg/docker-minecraft-server/pull/2148) for more information.
Please pull or build the latest docker image if your image is older than that!

If you are using an entirely different server image please verify that it is patched, especially check Bukkit 1.7.10!
