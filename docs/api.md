# API Documentation

This document provides a comprehensive overview of the API for the JPS-Prospect-Aggregate project.

## Table of Contents

- [Endpoints](#endpoints)
  - [Base URL](#base-url)
  - [Dashboard](#dashboard)
  - [Proposals](#proposals)
  - [Data Sources](#data-sources)
  - [Health Check](#health-check)
- [Data Models](#data-models)
  - [Proposal](#proposal)
  - [DataSource](#datasource)
  - [ScraperStatus](#scraperstatus)
  - [Pagination](#pagination)
  - [Error](#error)

## Endpoints

### Base URL

All API endpoints are relative to the base URL:

```
/api/v1
```

### Dashboard

#### Get Dashboard Data

```
GET /dashboard
```

Returns overview statistics and metrics for the dashboard.

**Response:**

```json
{
  "status": "success",
  "data": {
    "counts": {
      "total_proposals": 120,
      "total_sources": 5
    },
    "recent_proposals": [
      {
        "id": 123,
        "title": "Office Renovation",
        "agency": "Department of Administration",
        "release_date": "2023-05-10T09:00:00Z",
        "response_date": "2023-06-15T14:30:00Z",
        "estimated_value": 75000,
        "status": "active"
        // Additional proposal fields...
      }
    ]
  }
}
```

### Proposals

#### Get Proposals

```
GET /proposals
```

Returns a list of proposals with pagination.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| page | number | No | Page number (default: 1) |
| per_page | number | No | Items per page (default: 50, max: 500) |
| sort_by | string | No | Field to sort by (release_date, title, agency, value, status, naics_code, created_at, updated_at) |
| sort_order | string | No | Sort order (asc, desc) |

**Response:**

```json
{
  "status": "success",
  "data": [
    {
      "id": 123,
      "source_id": 1,
      "external_id": "ABC123",
      "title": "Office Renovation",
      "agency": "Department of Administration",
      "office": "Facilities Management",
      "description": "Complete renovation of the 3rd floor office space",
      "naics_code": "236220",
      "estimated_value": 75000,
      "release_date": "2023-05-10T09:00:00Z",
      "response_date": "2023-06-15T14:30:00Z",
      "contact_info": "John Smith, john.smith@example.gov, 555-123-4567",
      "url": "https://example.gov/proposals/ABC123",
      "status": "active",
      "last_updated": "2023-05-15T14:30:00Z",
      "imported_at": "2023-05-10T09:00:00Z",
      "contract_type": "Fixed Price",
      "set_aside": "Small Business",
      "competition_type": "Full and Open",
      "solicitation_number": "SOL-123-456",
      "award_date": null,
      "place_of_performance": "Washington, DC",
      "incumbent": "Previous Contractor Inc.",
      "source_name": "Federal Business Opportunities",
      "is_latest": true
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total_count": 120,
    "total_pages": 3
  }
}
```

### Data Sources

#### Get Data Sources

```
GET /data-sources
```

Returns a list of data sources.

**Response:**

```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "Federal Business Opportunities",
      "url": "https://sam.gov/",
      "description": "Official federal government procurement opportunities",
      "last_scraped": "2023-06-10T08:15:00Z",
      "status": "working",
      "last_checked": "2023-06-10T08:15:00Z",
      "proposalCount": 75
    }
  ]
}
```

#### Create Data Source

```
POST /data-sources
```

Creates a new data source.

**Request Body:**

```json
{
  "name": "State Procurement Portal",
  "url": "https://procurement.state.gov/",
  "description": "State government procurement opportunities"
}
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "id": 2,
    "name": "State Procurement Portal",
    "url": "https://procurement.state.gov/",
    "description": "State government procurement opportunities",
    "last_scraped": null,
    "status": "unknown",
    "last_checked": null,
    "proposalCount": 0
  },
  "message": "Data source created successfully"
}
```

#### Update Data Source

```
PUT /data-sources/:id
```

Updates an existing data source.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | number | Yes | Data source ID |

**Request Body:**

```json
{
  "name": "Updated Source Name",
  "description": "Updated description"
}
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "id": 2,
    "name": "Updated Source Name",
    "url": "https://procurement.state.gov/",
    "description": "Updated description",
    "last_scraped": null,
    "status": "unknown",
    "last_checked": null,
    "proposalCount": 0
  },
  "message": "Data source with ID 2 updated successfully"
}
```

#### Delete Data Source

```
DELETE /data-sources/:id
```

Deletes a data source.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | number | Yes | Data source ID |

**Response:**

```json
{
  "status": "success",
  "message": "Data source with ID 2 deleted successfully"
}
```

### Health Check

```
GET /health
```

Returns the health status of the application and its components.

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2023-06-15T14:30:00Z",
  "response_time": 0.125,
  "components": {
    "database": {
      "status": "healthy",
      "stats": {
        "connections": 5,
        "active_connections": 2
      }
    },
    "redis": {
      "status": "healthy"
    },
    "celery": {
      "status": "healthy",
      "stats": {
        "active_workers": 2,
        "worker_names": ["worker1", "worker2"],
        "active_tasks": 3
      }
    }
  },
  "system": {
    "os": "Linux",
    "python_version": "3.9.5",
    "cpu_usage": 25.5,
    "memory_usage": 60.2,
    "disk_usage": 45.7
  },
  "data_sources": [
    {
      "id": 1,
      "name": "Federal Business Opportunities",
      "last_scraped": "2023-06-10T08:15:00Z",
      "status": "working",
      "last_checked": "2023-06-10T08:15:00Z"
    }
  ],
  "version": "1.0.0"
}
```

## Data Models

### Proposal

Represents a business proposal opportunity.

| Field | Type | Description |
|-------|------|-------------|
| id | number | Unique identifier for the proposal |
| source_id | number | ID of the data source |
| external_id | string | External identifier from the source system |
| title | string | Title of the proposal |
| agency | string | Agency issuing the proposal |
| office | string | Office within the agency |
| description | string | Detailed description of the proposal |
| naics_code | string | North American Industry Classification System code |
| estimated_value | number | Estimated monetary value of the proposal |
| release_date | string | Date when the proposal was released (ISO 8601) |
| response_date | string | Deadline for responding to the proposal (ISO 8601) |
| contact_info | string | Contact information for inquiries |
| url | string | URL to the original proposal |
| status | string | Status of the proposal |
| last_updated | string | Last update timestamp (ISO 8601) |
| imported_at | string | When the proposal was imported (ISO 8601) |
| contract_type | string | Type of contract (Fixed Price, Cost Plus, etc.) |
| set_aside | string | Set-aside category (Small Business, 8(a), etc.) |
| competition_type | string | Type of competition (Full and Open, etc.) |
| solicitation_number | string | Solicitation number |
| award_date | string | Date when the contract was awarded (ISO 8601) |
| place_of_performance | string | Location where work will be performed |
| incumbent | string | Current contractor (if applicable) |
| source_name | string | Name of the data source |
| is_latest | boolean | Whether this is the latest version of the proposal |

### DataSource

Represents a source of proposal data.

| Field | Type | Description |
|-------|------|-------------|
| id | number | Unique identifier for the data source |
| name | string | Name of the data source |
| url | string | URL of the data source |
| description | string | Description of the data source |
| last_scraped | string | When the source was last scraped (ISO 8601) |
| status | string | Status of the scraper (working, not_working, unknown) |
| last_checked | string | When the status was last checked (ISO 8601) |
| proposalCount | number | Number of proposals from this source |

### ScraperStatus

Represents the status of a scraper for a data source.

| Field | Type | Description |
|-------|------|-------------|
| id | number | Unique identifier for the status record |
| source_id | number | ID of the data source |
| status | string | Status of the scraper (working, not_working, unknown) |
| last_checked | string | When the status was last checked (ISO 8601) |
| error_message | string | Error message if the scraper failed |
| response_time | number | Response time in seconds |

### Pagination

Represents pagination information for list endpoints.

| Field | Type | Description |
|-------|------|-------------|
| page | number | Current page number (1-based) |
| per_page | number | Number of items per page |
| total_count | number | Total number of items |
| total_pages | number | Total number of pages |

### Error

Represents an error response.

| Field | Type | Description |
|-------|------|-------------|
| status | string | Always "error" for error responses |
| error | object | Error details |
| error.code | string | Error code |
| error.message | string | Human-readable error message |
| error.details | object | Additional error details (optional) |

Example:
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "name": "Name is required"
    }
  }
}
``` 