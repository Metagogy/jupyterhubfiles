"""
JupyterHub config for the littlest jupyterhub.
"""
import subprocess
from glob import glob
import os
import git,  shutil
from pwd import getpwnam
#import grp
#from pathlib import Path  

from systemdspawner import SystemdSpawner
from tljh import configurer, user
from tljh.config import INSTALL_PREFIX, USER_ENV_PREFIX, CONFIG_DIR
from tljh.normalize import generate_system_username
from tljh.utils import get_plugin_manager
from jupyterhub_traefik_proxy import TraefikTomlProxy

from traitlets import Dict, Unicode, List



class UserCreatingSpawner(SystemdSpawner):
    """
    SystemdSpawner with user creation on spawn.

    FIXME: Remove this somehow?
    """
    user_groups = Dict(key_trait=Unicode(), value_trait=List(Unicode()), config=True)

    def start(self):
       
        system_username = generate_system_username('jupyter-'+ self.user.name)

        # FIXME: This is a hack. Allow setting username directly instead
        self.username_template = system_username
        user.ensure_user(system_username)
        user.ensure_user_group(system_username, 'jupyterhub-users')
        if self.user.admin:
            user.ensure_user_group(system_username, 'jupyterhub-admins')
        else:
            user.remove_user_group(system_username, 'jupyterhub-admins')
        if self.user_groups:
            for group, users in self.user_groups.items():
                if self.user.name in users:
                    user.ensure_user_group(system_username, group)
        return super().start()

c.JupyterHub.spawner_class = UserCreatingSpawner
# leave users running when the Hub restarts
c.JupyterHub.cleanup_servers = False

# Use a high port so users can try this on machines with a JupyterHub already present
c.JupyterHub.hub_port = 15001

c.TraefikTomlProxy.should_start = False

dynamic_conf_file_path = os.path.join(INSTALL_PREFIX, 'state', 'rules', 'rules.toml')
c.TraefikTomlProxy.toml_dynamic_config_file = dynamic_conf_file_path
c.JupyterHub.proxy_class = TraefikTomlProxy

c.SystemdSpawner.extra_paths = [os.path.join(USER_ENV_PREFIX, 'bin')]
c.SystemdSpawner.default_shell = '/bin/bash'
# Drop the '-singleuser' suffix present in the default template
c.SystemdSpawner.unit_name_template = 'jupyter-{USERNAME}'

tljh_config = configurer.load_config()
configurer.apply_config(tljh_config, c)

# Let TLJH hooks modify `c` if they want

## iframe

c.JupyterHub.tornado_settings = {
    'headers': {
         'Content-Security-Policy': 'frame-ancestors self https://www.aieducator.com',

    }
}


##After login
#c.NotebookApp.tornado_settings={
#  "headers":{
#    "Content-Security-Policy": "frame-ancestors self  https://aieducator.com",
#  }
#}




# Call our custom configuration plugin
pm = get_plugin_manager()
pm.hook.tljh_custom_jupyterhub_config(c=c)

# Load arbitrary .py config files if they exist.
# This is our escape hatch
extra_configs = sorted(glob(os.path.join(CONFIG_DIR, 'jupyterhub_config.d', '*.py')))
for ec in extra_configs:
    load_subconfig(ec)




#Assignment
ERASE_DIR = True

def clone_repo(uid,username, git_url, repo_dir):
    
    git.Repo.clone_from(git_url, repo_dir)
    
#    shutil.copytree(repo_dir,'home/jupyter-{username}')
    try:
        getpwnam(username)
    except KeyError:
    	subprocess.check_call(['useradd', '-ms', '/bin/bash', username])
    uid = getpwnam(username).pw_uid
    gid = getpwnam(username).pw_gid
    for root, dirs, files in os.walk(repo_dir):
      for d in dirs:
            shutil.chown(os.path.join(root, d), user=uid, group=gid)
#           subprocess.call(['chmod', '777', d])
      for f in files:
            shutil.chown(os.path.join(root, f), user=uid, group=gid)
#            subprocess.call(['chmod', '700', f])





def create_dir_hook(spawner):

    username = spawner.user.name
    uid = spawner.user.id
    DIR_NAME = os.path.join("/home", username)
    git_url = "https://github.com/Metagogy/ML-BootCAMP-Assignments.git"
    repo_dir = os.path.join(DIR_NAME, 'Assignments')

    if ERASE_DIR == True:
        if os.path.isdir(repo_dir):
           shutil.rmtree(repo_dir)
        os.makedirs(repo_dir)
        clone_repo(uid,username, git_url, repo_dir)

    if ERASE_DIR == False and not (os.path.isdir(repo_dir)):
        os.makedirs(repo_dir)
        clone_repo(uid,username, git_url, repo_dir)

    if ERASE_DIR == False and os.path.isdir(repo_dir):
        pass

c.Spawner.pre_spawn_hook = create_dir_hook

## Home folder 
c.Spawner.notebook_dir = '/home/{username}'



