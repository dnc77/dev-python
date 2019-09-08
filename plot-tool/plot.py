import pandas
import sqlite3
import urllib.parse
import plotly.express as plotly

# Url encode a string
def urlenc(str):
   return urllib.parse.quote(str)

# Connect to database.
def connect():
   try:
      conn = sqlite3.connect('local.db')

      # Create any desired functions in sqlite.
      conn.create_function('urlenc', 1, urlenc)
   except Error as e:
      print(e)

   return conn

def fetchdata(cnect):
   try:
      # Define our data query.
      sql = 'select           distinct ' + \
            '                 be.censusyear, be.cluesmallarea, ' + \
            '                 be.industrydescription, ' + \
            '                 oscp.parkingspaces, ' + \
            '                 ebb.totalemploymentinblock ' + \
            'from             businessestablishment be ' + \
            'inner join       offstreetcarpark oscp ' + \
            'on               oscp.blockid = be.blockid ' + \
            'and              oscp.propertyid = be.propertyid ' + \
            'and              oscp.basepropertyid = be.basepropertyid ' + \
            'inner join       employmentbyblocks ebb ' + \
            'on               ebb.censusyear = be.censusyear ' + \
            'and              ebb.blockid = be.blockid ' + \
            'order by         ebb.censusyear desc ' + \
            'limit            250; '

      # Retrieve the data.
      rows = pandas.read_sql_query(sql, cnect)
   except Error as e:
      print(e)
   
   return rows


# Connect to data source.
cnect = connect()
data = fetchdata(cnect)

# Plot it.
graphs = plotly.scatter(data,
            color='cluesmallarea',
            x='parkingspaces',
            y='industrydescription',
            size='totalemploymentinblock')

graphs.show()
