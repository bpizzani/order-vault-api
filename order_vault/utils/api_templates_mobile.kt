        submitButton.setOnClickListener {
            Toast.makeText(this, "Button clicked", Toast.LENGTH_SHORT).show()

            val visitorId = visitorId //generateFakeFingerprint()
            val localSessionId = localSessionId

            val json = JSONObject().apply {
                put("email", emailInput.text.toString())
                put("phone", phoneInput.text.toString())
                put("name", nameInput.text.toString())
                put("card", cardInput.text.toString())
                put("promo", promoInput.text.toString())
                put("user_id", userId)
                put("device_id", visitorId)
                put("local_session_id", localSessionId)
            }


            val attributeTypes = listOf("device_id", "phone", "card_details", "email", "local_session_id","checkout_id","user_id","order_id","session_id")
            val checkoutId = generateCheckoutId().toString().orEmpty()
            val orderId = generateOrderId().toString().orEmpty()

            val values = mapOf(
                "device_id" to visitorId.toString().orEmpty(),
                "phone" to phoneInput.text.toString().orEmpty(),
                "email" to emailInput.text.toString().orEmpty(),
                //"name" to nameInput.text.toString().orEmpty(),
                "promocode" to promoInput.text.toString().orEmpty(),
                "card_details" to cardInput.text.toString().orEmpty(),
                "user_id" to userId.toString().orEmpty(),
                "local_session_id" to localSessionId.orEmpty(),
                "session_id" to localSessionId.orEmpty(),
                "order_id" to orderId, // risk evaluation event save
                "id" to orderId, // finalize order save
                "checkout_id" to checkoutId, // risk evaluation event save
                "created_at" to ZonedDateTime.now().format(DateTimeFormatter.ISO_OFFSET_DATE_TIME).toString().orEmpty(), // also generated on backened just in case
            )

            CoroutineScope(Dispatchers.IO).launch {
                val riskResponse = riskApi(
                    attributeTypes = attributeTypes,
                    values = values,
                    promocode = promoInput.text.toString(),
                    apiKey = "abcde",
                    clientId = "client_c"
                )

                withContext(Dispatchers.Main) {
                    if (riskResponse["overall_abusive"] == true) {
                        Log.w("Rediim", "PROMO ABUSE!")
                        Toast.makeText(
                            this@MainActivity,
                            "PROMO ABUSE - Device or Phone or Card is already associated with more than one account",
                            Toast.LENGTH_LONG
                        ).show()
                    } else {
                        CoroutineScope(Dispatchers.IO).launch {
                            val result = finalizeOrderApi(JSONObject(values), "abcde", "client_c")
                            Log.d("Rediim", "Finalize API response: $result")

                            withContext(Dispatchers.Main) {
                                if (result["status"] == "failed") {
                                    Toast.makeText(this@MainActivity, "Finalize failed: ${result["error"]}", Toast.LENGTH_LONG).show()
                                } else {
                                    Toast.makeText(this@MainActivity, "Finalize success ✅", Toast.LENGTH_LONG).show()
                                }
                            }
                        }




                    }
                }
            }

            //sendToBackend(json) // FLASK Client backend API call
        }


// Rediim Risk Evaluation API
    fun riskApi(
        attributeTypes: List<String>,
        values: Map<String, String>,
        promocode: String? = null,
        apiKey: String,
        clientId: String
    ): Map<String, Any> {
        val client = OkHttpClient()
        val baseUrl = "https://api.rediim.com/api/evaluate".toHttpUrlOrNull() ?: return mapOf("error" to "Invalid URL")

        val urlBuilder = baseUrl.newBuilder()
            .addQueryParameter("attribute_types", attributeTypes.joinToString(","))

        // Add values for each attribute type
        for (attribute in attributeTypes) {
            values[attribute]?.let {
                urlBuilder.addQueryParameter(attribute, it)
            }
        }

        promocode?.let {
            urlBuilder.addQueryParameter("promocode", it)
        }

        val request = Request.Builder()
            .url(urlBuilder.build())
            .addHeader("X-API-KEY", apiKey)
            .addHeader("X-CLIENT-ID", clientId)
            .get()
            .build()

        return try {
            client.newCall(request).execute().use { response ->
                val bodyString = response.body?.string()
                if (response.isSuccessful && bodyString != null) {
                    val json = JSONObject(bodyString)
                    mapOf("overall_abusive" to json.optBoolean("overall_abusive", false))
                } else {
                    mapOf("error" to "Error: ${response.code} - ${response.message}")
                }
            }
        } catch (e: Exception) {
            mapOf("error" to "Request failed: ${e.message}")
        }
    }

    // Rediim Finalize Order API
    suspend fun finalizeOrderApi(
        orderData: JSONObject,
        apiKey: String,
        clientId: String
    ): Map<String, Any> {
        val client = OkHttpClient()
        val finalizeUrl = "https://api.rediim.com/finalize-order"

        val body = orderData.toString().toRequestBody("application/json".toMediaTypeOrNull())

        val request = Request.Builder()
            .url(finalizeUrl)
            .post(body)
            .addHeader("Content-Type", "application/json")
            .addHeader("X-API-KEY", apiKey)
            .addHeader("X-CLIENT-ID", clientId)
            .build()

        return try {
            client.newCall(request).execute().use { response ->
                val bodyString = response.body?.string()
                if (response.isSuccessful && bodyString != null) {
                    val json = JSONObject(bodyString)
                    json.keys().asSequence().associateWith { key -> json.get(key) } // Converts JSONObject to Map<String, Any>
                } else {
                    mapOf("status" to "failed", "error" to "Error: ${response.code} - ${response.message}")
                }
            }
        } catch (e: Exception) {
            mapOf("status" to "failed", "error" to "Request failed: ${e.message}")
        }
    }
