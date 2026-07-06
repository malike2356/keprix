# Trello REST API quick reference

Base URL: `https://api.trello.com/1`

Auth on every request: `key=$TRELLO_API_KEY&token=$TRELLO_TOKEN`

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/members/me` | Verify token; read member profile |
| GET | `/members/me/boards` | List boards for the token owner |
| GET | `/boards/{id}` | Board metadata |
| GET | `/boards/{id}/lists` | Lists on a board |
| GET | `/boards/{id}/cards` | Cards on a board (`?filter=open` for open only) |
| GET | `/lists/{id}/cards` | Cards in one list |
| GET | `/cards/{id}` | Single card |
| POST | `/cards` | Create card (`name`, `idList` required in JSON body) |
| PUT | `/cards/{id}` | Update card (`idList`, `due`, `name`, `desc`, `closed`, etc.) |
| POST | `/cards/{id}/actions/comments` | Add comment (`text` in body) |
| GET | `/boards/{id}/labels` | Labels on a board |

Official docs: https://developer.atlassian.com/cloud/trello/rest/
