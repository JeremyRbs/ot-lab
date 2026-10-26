# ot-lab

Banc d'essai personnel pour la sécurité des systèmes industriels (OT).
Objectif : comprendre, attaquer et défendre un environnement de contrôle-commande réaliste,
dans un cadre 100 % légal (matériel et logiciels m'appartenant).

## Architecture
- **Automate** : OpenPLC runtime (Raspberry Pi / Docker)
- **HMI** : interface de supervision
- **Protocole** : Modbus/TCP
- **Outils attaque** : Wireshark, scapy, pymodbus
- **Défense** : segmentation réseau, filtrage, supervision

## Plan
- [ ] Montage du banc (OpenPLC + HMI + Modbus/TCP)
- [ ] Simulation d'un processus simple (régulation de température)
- [ ] Capture et lecture du trafic Modbus
- [ ] Rejeu et altération de commandes (attaque)
- [ ] Mise en place des défenses (segmentation, filtrage, supervision)
- [ ] Write-up #1 : découverte → attaque → défense

## Journal
- **J1** : création du repo, commande du matériel.
