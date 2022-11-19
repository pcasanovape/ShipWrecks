from concurrent.futures import process
from sys import prefix
from warnings import filters
from scrapy import Spider, Request
from scrapy.crawler import CrawlerProcess
from bs4 import BeautifulSoup, SoupStrainer
import numpy as np
import pandas as pd
import re

class ShipWreckSpider(Spider):
    name = 'shipwreck'
    allowed_domains = ['en.wikipedia.org']
    start_urls = ['https://en.wikipedia.org/wiki/Lists_of_shipwrecks']
    base='https://en.wikipedia.org'
    taules=[]

    def start_requests(self):
        for u in self.start_urls:
            yield Request(u, callback=self.parse_main)  

    #procesem la pagina principal
    def parse_main(self, response):  

        data=response.xpath("//a[not(ancestor::table) and starts-with(@title, 'List of shipwrecks')]")       
        for link in data:
            next_page_url ='https://en.wikipedia.org'+link.xpath('@href').extract()[0]
            print(next_page_url)
            yield Request(next_page_url,self.extract_page)
            


    #procesem cada subpagina
    def extract_page(self, response): 

        main_title=response.xpath("//span[contains(@class, 'mw-page-title-main')]/text()[1]").extract()[0]
        data=response.xpath(" //table[contains(@class, 'wikitable')]/preceding-sibling::*[self::h2 or self::h3 or self::h4][1] | //table[contains(@class, 'wikitable')]")
        data_titles=response.xpath("//span[contains(@class, 'mw-headline') and not(contains(@id, 'Further_reading')) and not(contains(@id, 'References'))  and not(contains(@id, 'External_links'))]/ancestor::*[self::h2 or self::h3 or self::h4][1]")
        zones =self.expand_zones(data_titles)   
        return self.parse_page(data,main_title,zones)

    #procesem la informacio de cada taula de la subpagina
    def parse_page(self,data,main_title,zones_expandit):

        main_title=main_title.replace("List of shipwrecks","").replace(" of ","").replace(" in the ","") 
        titol=""
        zones=["","","",""]
        dfs=[]
        init=True

        for info in data:

            dades=BeautifulSoup(info.get(), 'html5lib')
            tipus = dades.find('body').find_all(recursive=False)[0].name

            if tipus !='table':
                # buscame la llista de zones
                titol=dades.find('span').text
                index=int(tipus.replace("h", ""))-2
                for info_zones in zones_expandit:
                    if info_zones[index]==titol and int(info_zones[3])==index:         
                         zones=info_zones.copy()

            else:
                #creem files columnes i generem taula
                zones.insert(0, main_title)
                columnes = [cela.text.replace("\n","") for cela in dades.find_all('tr')[0].find_all('th')]
                columnes = ['Zona1','Zona2','Zona3','Zona4'] + columnes
                files_raw=dades.find("tbody").find_all('tr')       
            
                df=self.create_table(columnes,zones,files_raw)
                dfs.append(df)
        
        df_final=pd.concat(dfs, axis=0)
        self.taules.append(df)

    def create_table(self,columnes,zones,raw):

        files=[]  
        for info_fila in raw:
            fila= [cela.text.strip() for cela in info_fila.find_all(recursive=False)]
            fila = zones[:4] +fila

            if len(fila)< len(columnes):
                for i in range(len(columnes)-len(fila)):
                    fila.append("")

            if len(fila)> len(columnes):
                fila.pop()

            if len(fila)== len(columnes):
                files.append(fila)  
            else:
                print(columnes)
                print(fila)

        columnes.append("extra_links")      
        fila.append(''.join(str(link) for link in info_fila.find_all('a')))

        df=pd.DataFrame(files, columns=columnes)
        df.drop(index=df.index[0], axis=0,inplace=True)
        return df


    #obtenim el llistat de zones complet
    def expand_zones(self,titles):
        last_index=-1
        prefix=['','','','']
        llista=[]
        index=0
        for title in titles:
            dades=BeautifulSoup(title.get(), 'html5lib')
            index=dades.find('body').find_all(recursive=False)[0].name.replace("h", "")
            index=int(index)-2
            text=dades.find('span').text
            if  index > last_index:
                prefix[index] = text
            elif index == last_index:
                prefix[3]=last_index
                llista.append(prefix.copy())
                prefix[index] = text
            else:
                prefix[3]=last_index
                llista.append(prefix.copy())
                prefix[index+1] =""
                if index==0:
                    prefix=['','','','']
                else:
                    prefix[2] =""
                prefix[index] = text
            last_index=index
        prefix[3]=index
        llista.append(prefix.copy())
        return llista
           
process =CrawlerProcess()
process.crawl(ShipWreckSpider)
process.start()

df=pd.concat(ShipWreckSpider.taules, axis=0)
df.to_csv('test.csv')  
print(df)

