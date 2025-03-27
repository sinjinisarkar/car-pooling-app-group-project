document.addEventListener("DOMContentLoaded", function () {
    console.log("✅ pickup_tracking.js loaded");
    let rideId = document.getElementById("ride-id").value; // Get ride ID from HTML
    let userType = document.getElementById("user-type").value; // "passenger" or "driver"
    let rideDate = document.getElementById("ride-date")?.value;  // Optional chaining to avoid error for one-time rides
    let map = L.map("map").setView([51.505, -0.09], 13); // Default view
    let modalShown = false;
    let pickupAdjusted = false;
    let journeyStarted = false;

    // Add OpenStreetMap Tile Layer
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    let passengerMarker, driverMarker; // Markers for tracking

    // Passenger & Driver icons
    const passengerIcon = L.icon({
        iconUrl: "https://cdn-icons-png.flaticon.com/512/684/684908.png", // A person icon
        iconSize: [30, 30]
    });

    const driverIcon = L.icon({
        iconUrl: "https://cdn-icons-png.flaticon.com/512/1048/1048314.png", // A car icon
        iconSize: [30, 30]
    });

    /**
     * Function to send live location to backend (for both passenger & driver)
     */
    function updateLocation(role) {
        console.log(`Updating location for role: ${role}`); // 👈 Add this
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(position => {
                let lat = position.coords.latitude;
                let lon = position.coords.longitude;
    
                let apiEndpoint = role === "passenger" ? "/api/track_passenger_location" : "/api/track_driver_location";
    
                // Send location update to backend
                fetch(apiEndpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        ride_id: rideId,
                        ride_date: rideDate,  // ✅ Add this line
                        latitude: lat,
                        longitude: lon
                    })
                })
                .then(response => response.json())
                .then(data => {
                    console.log(`${role} location updated:`, data.message);
                    document.getElementById("status-message").innerText = data.message;
    
                    // Update or create marker
                    if (role === "passenger") {
                        if (passengerMarker) {
                            passengerMarker.setLatLng([lat, lon]);
                        } else {
                            passengerMarker = L.marker([lat, lon], { icon: passengerIcon }).addTo(map)
                                .bindPopup("Your location").openPopup();
                        }
                    } else {
                        if (driverMarker) {
                            driverMarker.setLatLng([lat, lon]);
                        } else {
                            driverMarker = L.marker([lat, lon], { icon: driverIcon }).addTo(map)
                                .bindPopup("Driver's location").openPopup();
                        }
                    }
                });
            });
        }
    }

    /**
     * Fetch pickup location and show on map
     */
    fetch(`/api/get_pickup_location/${rideId}`)
        .then(response => response.json())
        .then(data => {
            let address = data.from_location;

            // Get coordinates of the pickup location
            fetch(`https://nominatim.openstreetmap.org/search?q=${address}&format=json`)
                .then(response => response.json())
                .then(geoData => {
                    if (geoData.length > 0) {
                        let pickupLat = parseFloat(geoData[0].lat);
                        let pickupLon = parseFloat(geoData[0].lon);

                        // Add pickup location marker
                        L.marker([pickupLat, pickupLon]).addTo(map)
                            .bindPopup("Pickup Location")
                            .openPopup();

                        map.setView([pickupLat, pickupLon], 14);
                    }
                });
        });

    let rideDateInput = document.getElementById("ride-date");
    rideDate = rideDateInput ? rideDateInput.value : null;
    /**
     * Function to fetch and display both driver & passenger live locations
     */
    function fetchLiveLocations() {
        const endpoint = rideDate 
            ? `/api/get_commute_live_locations/${rideId}/${rideDate}`
            : `/api/get_live_locations/${rideId}`;
        fetch(endpoint)
            .then(response => response.json())
            .then(data => {
                console.log("Live locations response:", data);
                // Clear old markers (optional, based on how you're managing updates)
                if (passengerMarker) {
                    map.removeLayer(passengerMarker);
                    passengerMarker = null;
                }
                if (driverMarker) {
                    map.removeLayer(driverMarker);
                    driverMarker = null;
                }
    
                let passengerLatLng = null;
                let driverLatLng = null;
    
                // 🧍 Passenger Marker
                if (data.passenger) {
                    let [pLat, pLon] = data.passenger;
    
                    // Check if overlapping with driver
                    if (data.driver && Math.abs(pLat - data.driver[0]) < 0.00001 && Math.abs(pLon - data.driver[1]) < 0.00001) {
                        // Slight offset to visually distinguish
                        pLat += 0.00005;
                        pLon += 0.00005;
                    }
    
                    passengerLatLng = [pLat, pLon];
                    const passengerPopup = userType === "passenger" ? "Your location" : "Passenger's location";
                    passengerMarker = L.marker(passengerLatLng, { icon: passengerIcon })
                        .addTo(map)
                        .bindPopup(passengerPopup)
                        .openPopup();
                }
    
                // 🚗 Driver Marker
                if (data.driver) {
                    const [dLat, dLon] = data.driver;
                    driverLatLng = [dLat, dLon];
                    const driverPopup = userType === "driver" ? "Your location" : "Driver's location";
                    driverMarker = L.marker(driverLatLng, { icon: driverIcon })
                        .addTo(map)
                        .bindPopup(driverPopup)
                        .openPopup();
                }
    
                // 🔍 Fit both markers in view
                if (driverMarker && passengerMarker) {
                    const group = new L.featureGroup([driverMarker, passengerMarker]);
                    map.fitBounds(group.getBounds().pad(0.3));
                }
    
                // Show modal if driver and passenger are nearby (driver only)
                if (data.nearby && userType === "driver" && !modalShown && !journeyStarted) {
                    const modal = document.getElementById("startJourneyModal");
                    const closeBtn = document.getElementById("closeModalBtn");
                    const startBtn = document.getElementById("startJourneyBtn");

                    console.log("Nearby detected! Showing modal...");
                    modal.style.display = "block";
                    // Move modalShown = true ONLY inside the Start button click

                    if (closeBtn) {
                        closeBtn.addEventListener("click", () => {
                            modal.style.display = "none";
                            modalShown = true;
                        });
                    }

                    if (startBtn) {
                        startBtn.addEventListener("click", () => {
                            console.log("Start Journey clicked");
                            fetch("/api/start_journey", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ ride_id: rideId })
                            })
                            .then(res => res.json())
                            .then(data => {
                                document.getElementById("status-message").innerText = data.message || "Journey started!";
                                modal.style.display = "none";
                                modalShown = true;
                                journeyStarted = true;
                            })
                            .catch(err => {
                                alert("Something went wrong.");
                                console.error(err);
                            });
                        });
                    }
                }

                // Show pickup adjust modal if driver is FAR and user is passenger
                if (
                    userType === "passenger" &&
                    data.passenger &&
                    data.driver &&
                    !pickupAdjusted &&
                    !modalShown
                  ) {
                    console.log("Showing pickup adjust modal for testing...");
                    modalShown = true;
                  
                    const adjustModal = document.getElementById("adjustPickupModal");
                    const adjustBtn = document.getElementById("adjustPickupBtn");
                    const closeBtn = document.getElementById("closeAdjustModal");
                  
                    adjustModal.style.display = "block";
                  
                    if (closeBtn) {
                      closeBtn.addEventListener("click", () => {
                        adjustModal.style.display = "none";
                      });
                    }
                  
                    if (adjustBtn) {
                      adjustBtn.addEventListener("click", () => {
                        adjustModal.style.display = "none";
                  
                        alert("Click on the map to set your pickup location.");
                        let tempMarker;
                        let adjusting = true;
                  
                        map.on("click", function (e) {
                          if (!adjusting) return;
                  
                          if (tempMarker) {
                            map.removeLayer(tempMarker);
                          }
                  
                          const { lat, lng } = e.latlng;
                          const newPickupIcon = L.icon({
                            iconUrl: "https://cdn-icons-png.flaticon.com/512/854/854878.png", // Different icon
                            iconSize: [30, 30]
                        });
                        
                        tempMarker = L.marker([lat, lng], {
                            icon: newPickupIcon,
                            draggable: true
                        }).addTo(map).bindPopup("New Pickup: drag and double-click to confirm").openPopup();
                  
                        tempMarker.on("dblclick", () => {
                            const newCoords = tempMarker.getLatLng();
                            sendUpdatedPickup(newCoords.lat, newCoords.lng);
                            adjusting = false;
                            // map.removeLayer(tempMarker);
                            map.off("click");
                          });
                        });
                  
                        function sendUpdatedPickup(lat, lon) {
                          fetch("/api/update_passenger_pickup_location", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ ride_id: rideId, latitude: lat, longitude: lon })
                          })
                            .then(res => res.json())
                            .then(data => {
                              alert(data.message || "Pickup location updated.");
                              pickupAdjusted = true;
                            })
                            .catch(err => {
                              alert("Error updating pickup location.");
                              console.error(err);
                            });
                        }
                      });
                    }
                  }
            })
            .catch(error => console.error("Error fetching live locations:", error));
    }
    

    // Fix Leaflet map rendering issue
    setTimeout(() => {
        map.invalidateSize();
    }, 500);

    if (userType === "passenger") {
        updateLocation("passenger");
        setTimeout(fetchLiveLocations, 1500); // Delay to allow backend to store location
    
        setInterval(() => {
            updateLocation("passenger");
            fetchLiveLocations();
        }, 10000);
    } else if (userType === "driver") {
        console.log("Driver detected");
        updateLocation("driver");
        setTimeout(fetchLiveLocations, 1500); // Delay to allow backend to store location
    
        setInterval(() => {
            updateLocation("driver");
            fetchLiveLocations();
        }, 10000);
    }
    

    // Tab Switching in dashboard
    let upcomingBtn = document.getElementById("showUpcoming");
    let publishedBtn = document.getElementById("showPublished");

    let upcomingSection = document.getElementById("upcomingSection");
    let publishedSection = document.getElementById("publishedSection");

    upcomingBtn.addEventListener("click", function() {
        upcomingSection.style.display = "block";
        publishedSection.style.display = "none";

        upcomingBtn.classList.add("active");
        publishedBtn.classList.remove("active");
    });

    publishedBtn.addEventListener("click", function() {
        upcomingSection.style.display = "none";
        publishedSection.style.display = "block";

        publishedBtn.classList.add("active");
        upcomingBtn.classList.remove("active");
    });

});
