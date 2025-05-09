import json
import requests
import os
import re
from urllib.parse import urlparse

def download_swagger_json(swagger_url):
    baseUrl = urlparse(swagger_url).netloc
    response = requests.get(swagger_url)
    response.raise_for_status()  # Levanta uma exceção se ocorrer um erro
    return (response.json(), baseUrl)

def resolve_ref(schema, definitions, resolved_refs=None):
    if resolved_refs is None:
        resolved_refs = set()

    if '$ref' in schema:
        ref = schema['$ref'].replace('#/definitions/', '')
        if ref in resolved_refs:
            return {}
        resolved_refs.add(ref)
        schema = definitions.get(ref, {}).copy()

    result = {}

    if "properties" in schema:
        for key, item in schema["properties"].items():
            if '$ref' in item:
                result[key] = resolve_ref(item, definitions, resolved_refs)
            else:
                # Definir valores padrão com base no tipo
                if item.get("type") == "integer":
                    result[key] = 0
                elif item.get("type") == "string":
                    result[key] = "string"
                elif item.get("type") == "boolean":
                    result[key] = True
                elif item.get("type") == "array":
                    result[key] = []
                    if "items" in item:
                        result[key] = [resolve_ref(item["items"], definitions, resolved_refs)]
                elif item.get("type") == "object":
                    result[key] = resolve_ref(item, definitions, resolved_refs)
    
    resolved_refs.clear()
    return result

def convert_swagger_to_postman(swagger_json, baseUrl, postman_collection_path):
    servers = swagger_json.get("servers", [])
    microService = f"{baseUrl}{servers[0]['url']}" if servers else "BaseURL"
    postman_collection = {
        "info": {
            "name": swagger_json.get('info', {}).get('title', 'Swagger Collection'),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "description": swagger_json.get('info', {}).get('description', '')
        },
        "item": [],
        "variable": [
            {
                "key": "baseUrl",
                "value": f"{microService}", 
                "type": "string"
            },
            {
                "key": "authToken",
                "value": "YOUR_TOKEN_HERE",
                "type": "string"
            },
            {
                "key": "version",
                "value": "1",
                "type": "string"
            }
        ]
    }

    # Organiza os requests por primeiro segmento do path
    paths_dict = {}

    for path, methods, in swagger_json.get('paths', {}).items():
        folder_name = methods.get(next(iter(methods))).get("tags")
        folder_name = folder_name[0] if folder_name is not None else path.strip('/').split('/')[2]

        path = re.sub(r'\{(?!\{)([^}]+)\}', r':\1', path)
        path = path.replace(":version", "{{version}}")
        

        # Verifica se a pasta já existe, caso contrário, cria uma nova
        if folder_name not in paths_dict:
            paths_dict[folder_name] = {
                "name": folder_name,
                "item": []
            }

        for method, details in methods.items():
            name = details.get("summary")
            item = {
                "name": name if name is not None else f"{path.strip('/').split('/')[-1]}",
                "request": {
                    "method": method.upper(),
                    "header": [],
                    "body": {},
                    "url": {
                        "raw": "{{baseUrl}}" + path,
                        "host": ["{{baseUrl}}"],
                        "path": path.strip('/').split('/'),
                        "query": [],
                    },
                    "description": details.get("description", "")
                },
                "response": []
            }

            if folder_name == "auth" and method.upper() == "POST":  
                item["event"] = [
                    {
                        "listen": "test",
                        "script": {
                            "exec": [
                                "if(pm.response.code === 200){\r",
                                "    var body = pm.response.json()\r",
                                "    pm.collectionVariables.set(\"token\", body.access_token);\r",
                                "    var data = JSON.parse(pm.request.body.raw)\r",
                                "    if(data.IntegrationKey){\r",
                                "        pm.collectionVariables.set(\"integrationKey\", data.IntegrationKey);\r",
                                "    }\r",
                                "}\r"
                            ],
                            "type": "text/javascript"
                        }
                    }
                ]

            # Processa parametros
            for param in details.get('parameters', []):
                if param.get('in') == 'header':
                    item['request']['header'].append({
                        "key": param['name'],
                        "value": "",
                        "description": param.get('description', "")
                    })
                elif param.get('in') == 'query':
                    item['request']['url']['query'].append({
                        "key": param['name'],
                        "value": "",
                        "description": param.get('description', "")
                    })
                elif param.get('in') == 'body' or param.get('in') == 'formData':
                    schema = param.get('schema', {})
                    schema = resolve_ref(schema, swagger_json['definitions'])
                    
                    item['request']['body'] = {
                        "mode": "raw",
                        "raw": json.dumps(schema, indent=4),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    }
              
            # Processa respostas
            for status, response in details.get('responses', {}).items():
                postman_response = {
                    "name": f"{status} response",
                    "originalRequest": item['request'],
                    "status": status,
                    "code": int(status),
                    "body": json.dumps(response.get('content', {}), indent=4),
                    "header": [],
                    "description": response.get('description', '')
                }
                item['response'].append(postman_response)

            # Adiciona o item à pasta correspondente
            paths_dict[folder_name]['item'].append(item)

    # Adiciona todas as pastas à coleção
    postman_collection['item'] = list(paths_dict.values())

    with open(postman_collection_path, 'w', encoding='utf-8') as f:
        json.dump(postman_collection, f, indent=4)

    print(f"Postman Collection saved to {postman_collection_path}")


def gen_collection(url, name):
    swagger_url = url.replace("index.html", "v1/docs.json")
    postman_collection_path = f"{name}_collection.json"

    swagger_data, baseUrl = download_swagger_json(swagger_url)
    convert_swagger_to_postman(swagger_data, baseUrl, postman_collection_path)
    input("Pressione Enter para sair...")

