.mode column
.headers on
select         distinct
               be.censusyear, be.cluesmallarea, be.tradingname,
               be.industrydescription, be.location,
               oscp.parkingspaces, ebb.totalemploymentinblock
from           businessestablishment be
inner join     offstreetcarpark oscp
on             oscp.blockid = be.blockid
and            oscp.propertyid = be.propertyid
and            oscp.basepropertyid = be.basepropertyid
inner join     employmentbyblocks ebb
on             ebb.censusyear = be.censusyear
and            ebb.blockid = be.blockid
order by       ebb.censusyear desc
limit          10




.mode column
.headers on
select         distinct
               be.censusyear, be.cluesmallarea,
               be.industrydescription,
               oscp.parkingspaces, ebb.totalemploymentinblock
from           businessestablishment be
inner join     offstreetcarpark oscp
on             oscp.blockid = be.blockid
and            oscp.propertyid = be.propertyid
and            oscp.basepropertyid = be.basepropertyid
inner join     employmentbyblocks ebb
on             ebb.censusyear = be.censusyear
and            ebb.blockid = be.blockid
order by       ebb.censusyear desc
limit          10;
