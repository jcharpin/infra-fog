#!/usr/bin/env python3

import smtplib
import email.utils
from email.mime.text import MIMEText
import subprocess
import argparse
import socket
import sys
import os

DEBUG=False
#Nom du serveur SMTP
SMTPSRV = ''
# Nom relatif du repertoire de sauvegarde des anciennes versions (man rsync)
BACKUPDIR = 'OLD'

# Create the message
def sendMsg(**kwargs):
    """Envoyer un message en passant par le serveur smtp interne"""
    
    if not 'to' in kwargs:
        return ("Pas d'adresse fournie, aucun mail envoye !")
    else:
        # initialiser nom du serveur envoyant mail
        fromsrv = socket.getfqdn()

        msg = MIMEText(kwargs['msg']) #initialiser mail meme si msg vide
        msg['To'] = email.utils.formataddr(('', kwargs['to']))
        msg['From'] = email.utils.formataddr((
            'root@' + fromsrv,
            'root@' + fromsrv))
      
    if kwargs['coderetour']:
        msg['Subject'] = 'Sauvegarde de {} : succes'.format(
                kwargs['srcsrv'],
                )
    else:
        msg['Subject'] = 'Sauvegarde de {} : echec'.format(
                kwargs['srcsrv'],
                )

    server = smtplib.SMTP(SMTPSRV, 25)

    # Si DEBUG on affiche la transaction smtp complete
    if not DEBUG:
        server.set_debuglevel(False)
    else:
        server.set_debuglevel(True)  # show communication with the server

    try:
        server.sendmail(
            'root@' + fromsrv,
            [kwargs['to']],
            msg.as_string(),
            )
    finally:
        server.quit()
        
    return ("Rapport envoyé !")

def execmd(**kwargs):
    """Execution des commandes shell"""

    # On parcourt la liste des commandes a effectuer
    proc = subprocess.Popen(
                        cmd,    
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        )

    stdout_value, stderr_value = proc.communicate()
    
    # Si erreur on sort et on retourne le message d'erreur
    if stderr_value:
            print("Une erreur est intervenue :\n {}".format(
                stderr_value.decode('utf-8'),
            ))
            return (0, stderr_value.decode('utf-8'))
    
    # Si pas d'erreur retour message de sortie
    else:
        print("La sortie du programme est :\n{}".format(
            stdout_value.decode('utf-8'),
        ))
        return (1, stdout_value.decode('utf-8'))
        

if __name__ == '__main__':
    
    # Recuperer la liste des arguments via le module 'argparse'    
    parser = argparse.ArgumentParser(description="Sauvegarder le contenu d'un \
        repertoire distant dans un repertoire local")
    parser.add_argument(
        "srcsrv", 
        type=str,
        help="serveur a sauvegarder (connexion SSH sans mot de passe requise)",
        )
    parser.add_argument(
        "srcrep", 
        type=str,
        help="repertoire distant a sauvegarder", 
        )
    parser.add_argument(
        "dstrep",
        type=str,
        help="repertoire local de sauvegarde",
    )
    parser.add_argument(
        "--adrmailifsuccess",
        type=str,
        help="Adresse mail destinataire pour message succes",
        )
    parser.add_argument(
        "--adrmailiferror",
        type=str,
        help="Adresse mail destinataire pour les cas d'echec",
        )
    args = parser.parse_args()

    # Initialisation du dictionnaire d'arguments pour les fcts
    kwargs = { 
                'srcsrv' : args.srcsrv,
                'srcrep' : args.srcrep.rstrip('/'),
                'dstrep' : args.dstrep.rstrip('/'),
            }

    # Initialiser le tuple qui contient les commandes a traiter avec les
    # arguments saisis
    cmds = (
       # commande rsync pour sauvegarde
       "rsync -rltogbpD --del --backup-dir=" + BACKUPDIR + 
       "/`date '+%Y%m%d.%H%M%S'` '-e ssh -o StrictHostKeyChecking=no' root@" 
       + args.srcsrv + ":" + kwargs['srcrep'] + " " + kwargs['dstrep'],
       
       # commande find pour nettoyage des fichiers plus vieux que 'x' mois
       "find " + os.path.join(kwargs['dstrep'], 'OLD') + " -maxdepth 1 "
       + "-mindepth 1 -ctime +180 -type d -exec rm -r {} \;"
       )
    
    # lancer chaque commande et recuperer sa sortie pour traitement... 
    for cmd in cmds :
        # Tester si commande contient 'rsync'
        if 'rsync' in cmd:
            rsyncflag = True
        else:
            rsyncflag = False

        # appeler fct execution de commande et recuperer code sortie
        kwargs['cmd'] = cmd
        coderetour, msg = execmd(**kwargs)

        # Quelle que soit la commande utilisee, si erreur on sort et
        # on envoie un mail si 'adressmailiferror' specifiee
        if not coderetour:
            # Initialiser arguments de la fct 'sendMsg'
            # seulement si 'adrmailiferrerror' existe
            try:
                kwargs['to'] = args.adrmailiferror
            except:
                pass
            else:
                kwargs['msg'] = msg
                kwargs['coderetour'] = coderetour
            finally:
                print("Erreur lors de :\n{}\nLe code retour est : {}".format(
                    cmd,
                    coderetour,
                ))

            # On sort de la boucle puisque erreur...
            break
    
        # Si 'coderetour' vaut 'True', si 'adrmailifsuccess' definie,
        # si rsyncflag -> preparer mail
        elif coderetour and args.adrmailifsuccess and rsyncflag:
            # seulement si 'adrmailifsuccess' existe
            try:    
                kwargs['to'] = args.adrmailifsuccess
            except:
                pass
            else:
                kwargs['coderetour'] = coderetour
                kwargs['msg'] = msg
            finally:
                print("Code retour de la commande 'rsync' :\n{}".format(
                    coderetour,
                ))

        # Dans tous les autres cas, on continue le parcours de la boucle
        # 'for' des differentes commandes.
        else:
            continue

    # Quand on sort de la boucle 'for', on verifie si le dictionnaire
    # d'arguments pour la fct 'sendMsg' est pret.
    # S'il l'est -> executer la fct d'envoi du rapport par mail ! 
    if 'to' in kwargs:
        sendMsg(**kwargs)

    # sortir
    sys.exit()
