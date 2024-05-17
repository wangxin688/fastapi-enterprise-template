# fastapi-enterprise-backend
Please notice that this project is still working in progress.
## feature
1. Class base view for better code structure and reduce the duplicate codes.
2. sqlalchemy asyncpg integration.
3. Generic DTO class for fast CRUD use. Which has good support for type hint friendly error message and power check for foreign key and unique constraints.
4. Jwt authentication with access token and refresh token.
5. RBAC with brand new way with fastapi operation id bounle to Role for flexible control. You can easy define every single API for every role.
6. Rye for python package and dependencies management. I use poerty before，it working perfect but sometimes very slowly to resolve dependencies.
7. Redis cache decorator integration for convenient api cache
8. Pytest and coverage inintegratio
9. Pre commit hooks with ruff for strong code style and lint checking
10. Basic user management with crud api.
11. I18N support for backed db and error message.
12. X-request-id for logging and request.
13. ...

## Project Structure

## planning
1. Fix some errors and type hint issues
2. Enhance DTO base for better crud support.
3. Release beta version.
4. enhance docs.
