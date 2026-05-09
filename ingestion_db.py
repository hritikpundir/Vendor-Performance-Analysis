import pandas as pd
import os
from sqlalchemy import create_engine
import logging
import time

logging.basicConfig(
    filename='logs/ingestion_db.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

engine = create_engine('sqlite:///inventory.db')

def ingest_db(table_name, df, engine):
    '''this function ingests a dataframe to the database'''
    df.to_sql(table_name, engine, if_exists='replace', index=False)


def load_raw_data():
    '''this function loads raw data from data/ directory to the database'''
    start = time.time()
    for file in os.listdir('data'):
        if '.csv' in file:
            df = pd.read_csv('data/' + file)
            logging.info(f'Ingesting {file} to db')
            ingest_db(file[:-4], df, engine)
    end = time.time()    
    total_time = (  end - start ) / 60 
    logging.info('-------Ingestion to db completed---------')  
    logging.info(f'Total time taken for ingestion to db: {total_time} minutes')      

if __name__ == '__main__':
    load_raw_data()    