from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os

# =========================================================
# CONFIGURACIÓN FASTAPI
# =========================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# =========================================================
# CONEXIÓN MONGODB
# =========================================================

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://SamuelV:Leono.li123$@proyecto4.ya83sqo.mongodb.net/DannAlpes?retryWrites=true&w=majority&appName=Proyecto4"
)

client = MongoClient(MONGO_URI)

db = client["DannAlpes"]

resenas = db["resenas"]

# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def serializar_documento(doc):

    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])

    return doc


def serializar_lista(lista):

    return [
        serializar_documento(doc)
        for doc in lista
    ]

# =========================================================
# RUTA BASE
# =========================================================

@app.get("/")
def inicio():

    return {
        "estado": "API Dann-Alpes funcionando"
    }

# =========================================================
# RF1 - CREAR RESEÑA
# =========================================================

@app.post("/resenas")
def crear_resena(datos: dict):

    datos["fecha"] = datetime.now().strftime("%Y-%m-%d")

    resultado = resenas.insert_one(datos)

    return {

        "mensaje": "Reseña creada correctamente",

        "id": str(resultado.inserted_id)
    }

# =========================================================
# RF2 - EDITAR RESEÑA
# =========================================================

@app.put("/resenas/{resena_id}")
def editar_resena(resena_id: str, datos: dict):

    resenas.update_one(

        {
            "_id": ObjectId(resena_id)
        },

        {
            "$set": {

                "comentario": datos["comentario"],

                "calificacion": datos["calificacion"]
            }
        }
    )

    return {

        "mensaje": "Reseña actualizada"
    }

# =========================================================
# RF3 - ELIMINAR RESEÑA
# =========================================================

@app.delete("/resenas/{resena_id}")
def eliminar_resena(resena_id: str):

    resenas.delete_one(

        {
            "_id": ObjectId(resena_id)
        }
    )

    return {

        "mensaje": "Reseña eliminada"
    }

# =========================================================
# RF4 - CONSULTAR RESEÑAS DE HOTEL
# =========================================================

@app.get("/hoteles/{hotel_id}/resenas")
def consultar_resenas_hotel(hotel_id: int):

    resultado = list(

        resenas.find(

            {
                "hotel.id": hotel_id
            }

        ).sort("calificacion", -1)

    )

    return serializar_lista(resultado)

# =========================================================
# RF5 - MARCAR RESEÑA COMO ÚTIL
# =========================================================

@app.post("/resenas/{resena_id}/util")
def marcar_util(resena_id: str, datos: dict):

    nuevo_voto = {

        "cliente_id": datos["cliente_id"]
    }

    resenas.update_one(

        {
            "_id": ObjectId(resena_id)
        },

        {
            "$push": {

                "votos_utiles": nuevo_voto
            }
        }
    )

    return {

        "mensaje": "Voto agregado"
    }

# =========================================================
# RF6 - HISTORIAL DE RESEÑAS CLIENTE
# =========================================================

@app.get("/clientes/{cliente_id}/resenas")
def historial_cliente(cliente_id: int):

    resultado = list(

        resenas.find(

            {
                "cliente.id": cliente_id
            }

        ).sort("fecha", -1)

    )

    return serializar_lista(resultado)

# =========================================================
# RF7 - RESPONDER RESEÑA
# =========================================================

@app.post("/resenas/{resena_id}/respuesta")
def responder_resena(resena_id: str, datos: dict):

    respuesta = {

        "administrador": {

            "id": datos["administrador_id"],

            "nombre": datos["nombre_admin"]
        },

        "comentario": datos["comentario"]
    }

    resenas.update_one(

        {
            "_id": ObjectId(resena_id)
        },

        {
            "$set": {

                "respuesta": respuesta
            }
        }
    )

    return {

        "mensaje": "Respuesta agregada"
    }

# =========================================================
# RF8 - ADMIN ELIMINA RESEÑA
# =========================================================

@app.put("/admin/resenas/{resena_id}/eliminar")
def admin_eliminar_resena(resena_id: str):

    resenas.delete_one(

        {
            "_id": ObjectId(resena_id)
        }
    )

    return {

        "mensaje": "Reseña eliminada por administrador"
    }

# =========================================================
# RF9 - DESTACAR RESEÑA
# =========================================================

@app.put("/resenas/{resena_id}/destacar")
def destacar_resena(resena_id: str):

    resena = resenas.find_one(

        {
            "_id": ObjectId(resena_id)
        }
    )

    if not resena:

        return {
            "error": "Reseña no encontrada"
        }

    hotel_id = resena["hotel"]["id"]

    # Quitar destacadas anteriores
    resenas.update_many(

        {
            "hotel.id": hotel_id
        },

        {
            "$set": {

                "destacada": 0
            }
        }
    )

    # Nueva destacada
    resenas.update_one(

        {
            "_id": ObjectId(resena_id)
        },

        {
            "$set": {

                "destacada": 1
            }
        }
    )

    return {

        "mensaje": "Reseña destacada"
    }

# =========================================================
# RFC1 - TOP HOTELES
# =========================================================

@app.get("/analytics/top-hoteles")
def top_hoteles():

    pipeline = [

        {
            "$group": {

                "_id": "$hotel.nombre",

                "promedio": {

                    "$avg": "$calificacion"
                }
            }
        },

        {
            "$sort": {

                "promedio": -1
            }
        },

        {
            "$limit": 10
        }
    ]

    resultado = list(

        resenas.aggregate(pipeline)
    )

    return resultado

# =========================================================
# RFC2 - EVOLUCIÓN HOTEL
# =========================================================

@app.get("/analytics/evolucion/{hotel_nombre}/{anio}")
def evolucion_hotel(hotel_nombre: str, anio: int):

    pipeline = [

        {
            "$match": {

                "hotel.nombre": hotel_nombre,

                "fecha": {

                    "$regex": f"^{anio}"
                }
            }
        },

        {
            "$group": {

                "_id": {

                    "mes": {

                        "$month": {

                            "$dateFromString": {

                                "dateString": "$fecha"
                            }
                        }
                    }
                },

                "promedio": {

                    "$avg": "$calificacion"
                },

                "total": {

                    "$sum": 1
                }
            }
        },

        {
            "$sort": {

                "_id.mes": 1
            }
        }
    ]

    resultado = list(

        resenas.aggregate(pipeline)
    )

    return resultado

# =========================================================
# RFC3 - COMPARACIÓN CIUDAD
# =========================================================

@app.get("/analytics/comparacion/{ciudad}")
def comparacion_ciudad(ciudad: str):

    pipeline = [

        {
            "$match": {

                "hotel.ciudad": ciudad
            }
        },

        {
            "$group": {

                "_id": "$hotel.nombre",

                "prom": {

                    "$avg": "$calificacion"
                },

                "total": {

                    "$sum": 1
                },

                "con_respuesta": {

                    "$sum": {

                        "$cond": [

                            {
                                "$ifNull": [
                                    "$respuesta",
                                    False
                                ]
                            },

                            1,

                            0
                        ]
                    }
                },

                "destacadas": {

                    "$sum": {

                        "$cond": [

                            {
                                "$eq": [
                                    "$destacada",
                                    1
                                ]
                            },

                            1,

                            0
                        ]
                    }
                }
            }
        },

        {
            "$project": {

                "promedio": "$prom",

                "total": 1,

                "porcentaje_resp": {

                    "$multiply": [

                        {
                            "$divide": [

                                "$con_respuesta",

                                "$total"
                            ]
                        },

                        100
                    ]
                },

                "porcentaje_destacadas": {

                    "$multiply": [

                        {
                            "$divide": [

                                "$destacadas",

                                "$total"
                            ]
                        },

                        100
                    ]
                }
            }
        },

        {
            "$sort": {

                "promedio": -1
            }
        }
    ]

    resultado = list(

        resenas.aggregate(pipeline)
    )

    return resultado