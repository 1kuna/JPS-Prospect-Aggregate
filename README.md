# JPS Proposal Forecast Aggregator

A dashboard application that scrapes data from various government procurement forecast sites and organizes them into a searchable, sortable dashboard.

## Features

- Automated scraping of procurement forecast data from government websites
- Data storage in a structured SQLite database (configurable for other databases)
- Web-based dashboard for viewing and analyzing procurement opportunities
- Filtering and sorting capabilities by various criteria
- Scheduled data refresh to keep information current
- Asynchronous task processing with Celery for improved performance
- Health monitoring of scrapers with automated alerts
- Robust logging with Loguru
- Type checking with MyPy
- Code formatting with Black
- Data validation with Pydantic

## Current Data Sources

- [Acquisition Gateway](https://acquisitiongateway.gov/forecast)
- [Social Security Administration](https://www.ssa.gov/oag/business/forecast.html)
- [Department of Commerce](https://www.commerce.gov/oam/industry/procurement-forecasts)
- [Department of Health and Human Services](https://osdbu.hhs.gov/industry/opportunity-forecast)
- [Department of Homeland Security](https://apfs-cloud.dhs.gov/forecast)
- [Department of Justice](https://www.justice.gov/jmd/doj-forecast-contracting-opportunities)
- [Department of Labor](https://acquisitiongateway.gov/forecast)
- [Department of State](https://www.state.gov/procurement-forecast)
- [Department of the Interior](https://acquisitiongateway.gov/forecast)
- [Department of the Treasury](https://osdbu.forecast.treasury.gov)
- [Department of Transportation](https://www.transportation.gov/osdbu/procurement-assistance/summary-forecast)
- [Department of Veterans Affairs](https://acquisitiongateway.gov/forecast)
- [General Services Administration](https://acquisitiongateway.gov/forecast)
- [Nuclear Regulatory Commission](https://acquisitiongateway.gov/forecast)
