# Tap n' tax demo server — standard library only, no pip.
# Sliplane / any Docker host: build from repo root, listens on $PORT (default 8080).
FROM python:3.12-slim
WORKDIR /app
COPY core ./core
COPY build ./build
COPY data ./data
COPY tests ./tests
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "python3 build/yearround/api.py ${PORT}"]
