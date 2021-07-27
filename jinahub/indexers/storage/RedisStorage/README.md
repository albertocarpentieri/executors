# ✨ RedisStorage

**RedisStorage** is Indexer wrapper around the redis server. Redis is an open source (BSD licensed), in-memory data structure store, used as a database, cache, and message broker. You can read more about it here: https://redis.io


<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [🌱 Prerequisites](#-prerequisites)
- [🚀 Usages](#-usages)
- [🎉️ Example](#%EF%B8%8F-example)
- [🔍️ Reference](#%EF%B8%8F-reference)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## 🌱 Prerequisites

- This Executor works on Python 3.7 and 3.8. 
- Make sure to install the [requirements](requirements.txt)

Additionally, you will need a running redis server. This can be a local instance, a Docker image, or a virtual machine in the cloud. To connect to redis, you need the hostname and the port. 

You can start one in a Docker container, like so: 

```bash
docker run -p 127.0.0.1:6379:6379/tcp -d redis
```

## 🚀 Usages

This indexer does not allow indexing two documents with the same `ID` and will issue a warning. It also does not allow updating a document by a non-existing ID and will issue a warning.

### 🚚 Via JinaHub

#### using docker images
Use the prebuilt images from JinaHub in your Python code: 

```python
from jina import Flow
	
f = Flow().add(uses='jinahub+docker://RedisStorage')
```

or in the `.yml` config.
	
```yaml
jtype: Flow
pods:
  - name: indexer
    uses: 'jinahub+docker://RedisStorage'
```

#### using source code
Use the source code from JinaHub in your Python code:

```python
from jina import Flow
	
f = Flow().add(uses='jinahub://RedisStorage')
```

or in the `.yml` config.

```yaml
jtype: Flow
pods:
  - name: indexer
    uses: 'jinahub://RedisStorage'
```


### 📦️ Via Pypi

1. Install the `executors` package.

	```bash
	pip install git+https://github.com/jina-ai/executors.git
	```

1. Use `executors` in your code

   ```python
   from jina import Flow
   from jinahub.indexers.storage.RedisStorage import RedisStorage
   
   f = Flow().add(uses=RedisStorage)
   ```


### 🐳 Via Docker

1. Clone the repo and build the docker image

	```shell
	git clone https://github.com/jina-ai/executors
	cd executors/jinahub/indexers/indexer/storage/RedisStorage
	docker build -t redis-storage .
	```

1. Use `redis-storage` in your code

	```python
	from jina import Flow
	
	f = Flow().add(uses='docker://redis-storage:latest')
	```
	

## 🎉️ Example 


```python
from jina import Flow, Document

f = Flow().add(uses='jinahub://RedisStorage')

with f:
    resp = f.post(on='/index', inputs=Document(), return_results=True)
    print(f'{resp}')
```

### Inputs 

Any type of `Document`.

### Returns

Nothing. The `Documents`s are stored.

## 🔍️ Reference

- https://redis.io