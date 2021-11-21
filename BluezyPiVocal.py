#encoding utf-8
'''
Created on 16 mai 2021

@author: Thomas
'''

import gtts
from pydub import AudioSegment
from pydub.playback import play
import os

DOSSIER_MP3 = "/home/pi/projet_bluetooth/mp3"
LISTE_MARC = ['MARC', 'Fairphone 3']

class BluezyPiVocal(object):
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        try :
            self.liste_mp3  = os.listdir(DOSSIER_MP3)
        except FileNotFoundError :
            raise

    def CheckUserName(self,user_name):
    
        if f'{user_name}.mp3' not in self.liste_mp3:
            if user_name in LISTE_MARC:
                name_to_pronounce = gtts.gTTS(text="Un mec chelou", lang='fr')
            else :
                name_to_pronounce = gtts.gTTS(text=user_name, lang='fr')
         
            name_to_pronounce.save(f'{DOSSIER_MP3}/{user_name}.mp3')

    
    def PronounceConnection(self,user_name):
        '''
        Annonce que user_name est connecté
        '''
        self.CheckUserName(user_name)
        
        user_sound =  AudioSegment.from_mp3(f'{DOSSIER_MP3}/{user_name}.mp3')
        action_sound = AudioSegment.from_mp3(f'{DOSSIER_MP3}/connection.mp3')
        play(user_sound)
        play(action_sound)

    def PronounceDisconnection(self, user_name):
        '''
        Annonce que user_name est déconnecté
        '''        
        self.CheckUserName(user_name)
        
        user_sound = AudioSegment.from_mp3(f'{DOSSIER_MP3}/{user_name}.mp3')
        action_sound = AudioSegment.from_mp3(f'{DOSSIER_MP3}/disconnection.mp3')
        play(user_sound)
        play(action_sound)
		
    def PronounceNoConnection(self):
        '''
        Annonce le timeout de connexion
        '''
        action_sound = AudioSegment.from_mp3(f'{DOSSIER_MP3}/no_connection.mp3')     
        play(action_sound)

   
    def PronounceErrorConnection(self, user_name):
        '''
        Annonce une erreur lors de la connexion de user
        '''
        self.CheckUserName(user_name)
        
        user_sound = AudioSegment.from_mp3(f'{DOSSIER_MP3}/{user_name}.mp3')
        action_sound = AudioSegment.from_mp3(f'{DOSSIER_MP3}/error_connection.mp3')      
        play(user_sound)
        play(action_sound)

if __name__=="__main__":
    module_vocal = BluezyPiVocal()
    module_vocal.PronounceDisconnection("Fairphone 3")
        
        