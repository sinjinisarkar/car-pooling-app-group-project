document.addEventListener("DOMContentLoaded", function () {
    let rideId = document.getElementById("ride-id").value; // Get ride ID from HTML
    let userType = document.getElementById("user-type").value; // "passenger" or "driver"
    let map = L.map("map").setView([51.505, -0.09], 13); // Default view

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
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(position => {
                let lat = position.coords.latitude;
                let lon = position.coords.longitude;

                let apiEndpoint = role === "passenger" ? "/api/track_passenger_location" : "/api/track_driver_location";

                // Send location update to backend
                fetch(apiEndpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ ride_id: rideId, latitude: lat, longitude: lon })
                })
                .then(response => response.json())
                .then(data => {
                    console.log(`${role} location updated:`, data.message);
                    document.getElementById("status-message").innerText = data.message;

                    // Update the correct marker
                    if (role === "passenger") {
                        if (passengerMarker) passengerMarker.remove();
                        passengerMarker = L.marker([lat, lon], { icon: passengerIcon }).addTo(map)
                            .bindPopup("Your location").openPopup();
                    } else {
                        if (driverMarker) driverMarker.remove();
                        driverMarker = L.marker([lat, lon], { icon: driverIcon }).addTo(map)
                            .bindPopup("Driver's location").openPopup();
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

    /**
     * Function to fetch and display both driver & passenger live locations
     */
    function fetchLiveLocations() {
        fetch(`/api/get_live_locations/${rideId}`)
            .then(response => response.json())
            .then(data => {
                if (data.passenger) {
                    if (passengerMarker) passengerMarker.remove();
                    passengerMarker = L.marker([data.passenger[0], data.passenger[1]], { icon: passengerIcon })
                        .addTo(map)
                        .bindPopup("Passenger's Location")
                        .openPopup();
                }

                if (data.driver) {
                    if (driverMarker) driverMarker.remove();
                    driverMarker = L.marker([data.driver[0], data.driver[1]], { icon: driverIcon })
                        .addTo(map)
                        .bindPopup("Driver's Location")
                        .openPopup();
                }

                if (data.nearby) {
                    alert("Driver and passenger are close to each other!");
                }
            });
    }

    // Fix Leaflet map rendering issue
    setTimeout(() => {
        map.invalidateSize();
    }, 500);

    // Update location every 30 seconds & fetch live locations
    if (userType === "passenger") {
        setInterval(() => {
            updateLocation("passenger");
            fetchLiveLocations(); // Fetch both driver & passenger locations
        }, 30000);
    } else if (userType === "driver") {
        setInterval(() => {
            updateLocation("driver");
            fetchLiveLocations(); // Fetch both driver & passenger locations
        }, 30000);
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
