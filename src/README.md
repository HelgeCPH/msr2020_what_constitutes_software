On Spet 9th 2019, I downloaded the YAML files from the [lingust repository](https://github.com/github/linguist)

```bash
wget https://raw.githubusercontent.com/github/linguist/master/lib/linguist/languages.yml
wget https://raw.githubusercontent.com/github/linguist/master/lib/linguist/vendor.yml
wget https://raw.githubusercontent.com/github/linguist/master/lib/linguist/documentation.yml
```

  * `vendor.yml` includes regexes for excluding vendored artifacts in linguist. That is, I can use this to identify vendored code and additional files
  * `documentation.yml` includes regexes for excluding documentation artifacts in linugist
  *


# Dependencies

`pip install PyGithub` for github API interaction
`conda install GitPython` for wrapping git CLI commands, such as `clone`

filemagic module

`brew install libmagic`
`pip install filemagic`

# Need a GitHub API Key


# Repeat the experiment

## Dependencies

  * To re-run the experiment you need to have [vagrant](https://www.vagrantup.com/downloads.html) installed.
  * The [vagrant digital ocean provider](https://github.com/devopsgroup-io/vagrant-digitalocean)

    ```bash
vagrant plugin install vagrant-digitalocean
```
  * The [vagrant scp plugin](https://github.com/invernizzi/vagrant-scp)

    ```bash
vagrant plugin install vagrant-scp
```

## Accounts

If you wnat to re-run the experiment at DigitalOcean, you have to be registered there and an API token available on your system under the environment variable `$DIGITAL_OCEAN_TOKEN` and your SSH key that you registered at DigitalOcean must be accessible as `$SSH_KEY_NAME`

## Running the Experiment

```bash
vagrant up experimentserver
vagrant ssh
```

```bash
nohup $HOME/main.sh &
```

Get all the results from remote machine:

```bash
vagrant scp 'experimentserver:/root/out/repos/*.zip' out/repos
vagrant scp 'experimentserver:/root/out/results/*.csv' out/results
vagrant scp 'experimentserver:/root/out/intermediate/*.csv' out/intermediate
```


## Run locally

```bash
python interpretation.py
```