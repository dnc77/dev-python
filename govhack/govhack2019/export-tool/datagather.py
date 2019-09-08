import pandas as pd
import sqlite3 as sql

sqlcon = sql.connect('local.db')

businessestablishments = \
   'Business_establishments.csv'
employmentbyblock = \
   'Employment_by_block_by_CLUE_industry(null_cleaned).csv'
offstreetcarparks = \
   'Off-street_car_parks_with_capacity_and_type(null_cleaned).csv'
pedcount2009 = 'pedcount2009.csv'

dfOffstreetcarparks = pd.read_csv(offstreetcarparks, sep=',')
dfEmploymentByBlock = pd.read_csv(employmentbyblock, sep=',')
dfBusinessEstablishments = pd.read_csv(businessestablishments, sep=',')
dfPedCount = pd.read_csv(pedcount2009, sep=',')

# Write to database tables.
dfOffstreetcarparks.to_sql('offstreetcarpark', sqlcon)
dfEmploymentByBlock.to_sql('employmentbyblocks', sqlcon)
dfBusinessEstablishments.to_sql('businessestablishment', sqlcon)
dfPedCount.to_sql('pedcount', sqlcon)

sqlcon.close()