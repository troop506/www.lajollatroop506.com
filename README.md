# Troop 506 Wordpress Docker


# Private Environment

The file ``private-environment.txt`` is encrypted to ``private-environment.txt.zip`` before committing to github, and the ``private-environment.txt`` file is ignored by git. The password for the file is stored as a secure note in the LastPass password manager. 

To encrypt:

    zip --password <password> private-environment.txt.zip private-environment.txt
    
To decrypt:

    unzip private-environment.txt.zip
    
Unless you are changing the password, you should only have to decrypt the file once after cloning the repo
