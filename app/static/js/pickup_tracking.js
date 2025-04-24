document.addEventListener("DOMContentLoaded", function () {
    let rideId = document.getElementById("ride-id").value; // Get ride ID from HTML
    let userType = document.getElementById("user-type").value; // "passenger" or "driver"
    let currentUsername = document.getElementById("current-username")?.value;
    let rideDate = document.getElementById("ride-date")?.value || null;  // chaining to avoid error for one-time rides
    let map = L.map("map", {
        maxZoom: 18  
    }).setView([51.505, -0.09], 13);
    const markerClusterGroup = L.markerClusterGroup();
    map.addLayer(markerClusterGroup);
    let modalShown = false;
    let pickupAdjusted = false;
    const startedPassengers = new Set();  // Tracks who has already been handled
    const dismissedPassengers = new Set();  // Tracks who was dismissed
    const dismissed = new Set();
    const reminderMap = {}; // username -> location
    let modalActive = false;
    let rideStatus = document.getElementById("ride-status")?.value || "unknown";
    let journeyStarted = (rideStatus === "ongoing");
    let journeyFinished = (rideStatus === "finished" || rideStatus === "completed" || rideStatus === "done");
    if (journeyStarted && !journeyFinished) {
        const finishBtn = document.getElementById("finishJourneyBtn");
        if (finishBtn) {
            finishBtn.style.display = "inline-block";
        }
    }

    if (journeyFinished) {
        const banner = document.getElementById("journeyFinishedBanner");
        const text = document.getElementById("journeyBannerText");

        if (userType === "driver") {
            text.innerText = "Journey finished. Thank you for driving with Catch My Ride.";
        } else {
            text.innerText = "Journey finished. Thank you for riding with Catch My Ride. Please rate your driver.";

            // Add Rate Button (passenger only)
            const rateBtn = document.createElement("button");
            rateBtn.innerText = "Rate Driver";
            rateBtn.className = "btn btn-light mt-4";
            rateBtn.style.fontSize = "1.2rem";

            rateBtn.onclick = function () {
                showRatingModal(rideId, rideDate);
            };

            if (!banner.querySelector(".rate-btn")) {
                rateBtn.classList.add("rate-btn"); 
                banner.appendChild(rateBtn);
            }
        }

        banner.style.display = "block";

        // Ensure finish button is hidden if journey is done
        const finishBtn = document.getElementById("finishJourneyBtn");
        if (finishBtn) {
            finishBtn.style.display = "none";
        }
    }


    // Helper: calculate distance between two lat/lon in meters
    function getDistanceFromLatLonInMeters(lat1, lon1, lat2, lon2) {
        const R = 6371000; // Earth radius in meters
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) *
            Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    // Add OpenStreetMap Tile Layer
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    let passengerMarker, driverMarker; // Markers for tracking

    // Passenger & Driver icons
    const passengerIcon = L.icon({
        iconUrl: "https://cdn-icons-png.flaticon.com/512/684/684908.png", // red pointer icon
        iconSize: [30, 30]
    });

    const driverIcon = L.icon({
        iconUrl: "https://cdn-icons-png.flaticon.com/512/1048/1048314.png", // car icon
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
                console.log(`📍 Got passenger location: ${lat}, ${lon}`);
    
                let apiEndpoint = role === "passenger" ? "/api/track_passenger_location" : "/api/track_driver_location";
    
                // Send location update to backend
                fetch(apiEndpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        ride_id: rideId,
                        ride_date: rideDate,  
                        latitude: lat,
                        longitude: lon
                    })
                })
                .then(response => response.json())
                .then(data => {
                    console.log(`${role} location updated:`, data.message);
                    document.getElementById("status-message").innerText = data.message;
                });
            });
        }
    }

    // Fetch pickup location and show on map
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
    
    // helper function for fetchLiveLocations()
    function startJourney() {
    
        fetch("/api/start_journey", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ride_id: rideId, ride_date: rideDate })
        })
        .then(res => res.json())
        .then(data => {
            document.getElementById("status-message").innerText = data.message || "Journey started!";
            journeyStarted = true;
            document.getElementById("ride-status").value = "ongoing";

            // Show the finish button
            const finishBtn = document.getElementById("finishJourneyBtn");
            if (finishBtn) {
                finishBtn.style.display = "inline-block";
            }
        })
        .catch(err => {
            alert("Something went wrong.");
            console.error(err);
        });
    }

    let rideDateInput = document.getElementById("ride-date");
    rideDate = rideDateInput ? rideDateInput.value : null;
    
    // Function to fetch and display both driver & passenger live locations
    function fetchLiveLocations() {
        markerClusterGroup.clearLayers();
        const endpoint = rideDate 
            ? `/api/get_commute_live_locations/${rideId}/${rideDate}`
            : `/api/get_live_locations/${rideId}`;
        fetch(endpoint)
            .then(response => response.json())
            .then(data => {
                console.log("Live locations response:", data);

                // Modal functionality (For commuting only) 
                if (userType === "driver" && typeof data.passenger === "object") {

                    const driverLoc = data.driver;
                    const passengers = data.passenger;

                    const usernames = Object.keys(passengers);

                    usernames.forEach(username => {
                        const [pLat, pLon] = passengers[username];

                        // Skip if already dismissed
                        if (dismissed.has(username)) return;

                        const distance = getDistanceFromLatLonInMeters(pLat, pLon, driverLoc[0], driverLoc[1]);
                        if (
                            distance <= 100 &&
                            !modalActive &&
                            !dismissedPassengers.has(username) &&
                            !startedPassengers.has(username) &&
                            !journeyStarted
                        ) {
                            modalActive = true;

                            // Update modal content
                            const modal = document.getElementById("startJourneyModal");
                            const closeBtn = document.getElementById("closeModalBtn");
                            const startBtn = document.getElementById("startJourneyBtn");
                            modal.querySelector("h4").innerText = `${username} is nearby`;
                            modal.style.display = "block";

                            // Close logic
                            closeBtn.onclick = () => {
                                dismissedPassengers.add(username);
                                modal.style.display = "none";
                                reminderMap[username] = [pLat, pLon];
                                modalActive = false;

                                // Create a reminder bar for this passenger
                                let reminderBar = document.createElement("div");
                                reminderBar.className = "alert alert-warning mt-2";
                                reminderBar.style.cursor = "pointer";
                                reminderBar.innerHTML = `${username} is still nearby. <u>Click to start journey</u>`;
                                reminderBar.id = `reminder-${username}`;
                                document.getElementById("reminder-container").appendChild(reminderBar);

                                // On click, start journey for that passenger
                                reminderBar.addEventListener("click", () => {
                                    startedPassengers.add(username);
                                    if (startedPassengers.size === usernames.length) {
                                        const finishBtn = document.getElementById("finishJourneyBtn");
                                        if (finishBtn) finishBtn.style.display = "inline-block";
                                        journeyStarted = true;
                                    }
                                    
                                    reminderBar.remove();
                                    console.log("Sending to /api/start_journey:", {
                                        ride_id: rideId,
                                        ride_date: rideDate
                                    });
                                    

                                    fetch("/api/start_journey", {
                                        method: "POST",
                                        headers: { "Content-Type": "application/json" },
                                        body: JSON.stringify({ ride_id: rideId, ride_date: rideDate })
                                    })
                                    .then(res => res.json())
                                    .then(data => {
                                        document.getElementById("status-message").innerText = data.message || "Location updated.";

                                    });
                                });
                            };

                            // Start logic (modal)
                            startBtn.onclick = () => {
                                startedPassengers.add(username);
                                modal.style.display = "none";
                                modalActive = false;
                                // journeyStarted = true;
                                console.log("Sending to /api/start_journey:", {
                                    ride_id: rideId,
                                    ride_date: rideDate
                                });

                                fetch("/api/start_journey", {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({ ride_id: rideId, ride_date: rideDate })
                                })
                                .then(res => res.json())
                                .then(data => {
                                    document.getElementById("status-message").innerText = data.message || "Location updated.";
                                    const multiReminder = document.getElementById("multi-reminder");
                                    if (multiReminder) {
                                        multiReminder.style.display = "none";
                                    }
                                });
                            };
                        }
                    });
                }
                // Clear old markers 
                if (passengerMarker) {
                    map.removeLayer(passengerMarker);
                    passengerMarker = null;
                }
                if (driverMarker) {
                    map.removeLayer(driverMarker);
                    driverMarker = null;
                }
    
                let driverLatLng = null;
                let allMarkers = [];

                if (data.passenger) {
                    if (Array.isArray(data.passenger)) {
                        console.log("One-time ride detected");
                    } else {
                        console.log("Commuting ride detected");
                    }
                }

                // Multiple Passenger Markers (for both one time and commuting)
                if (data.passenger && typeof data.passenger === "object" && !Array.isArray(data.passenger)) {
                    console.log("Detected commuting ride mode: rendering multiple passenger markers");
                    const passengerCount = Object.keys(data.passenger).length;
                    console.log(`👥 Number of passengers found: ${passengerCount}`);
    
                    for (const [passengerKey, coords] of Object.entries(data.passenger)) {
                        let [pLat, pLon] = coords;

                        // Don't show other passengers to a passenger
                        if (userType === "passenger" && passengerKey !== currentUsername) continue;

                        // Check if overlapping with driver
                        if (data.driver && Math.abs(pLat - data.driver[0]) < 0.00001 && Math.abs(pLon - data.driver[1]) < 0.00001) {
                            pLat += 0.00005;
                            pLon += 0.00005;
                        }

                        const marker = L.marker([pLat, pLon], { icon: passengerIcon })
                        .bindPopup(userType === "passenger" ? "Your location" : `Passenger: ${passengerKey}`);
                    
                        markerClusterGroup.addLayer(marker);
                        allMarkers.push(marker);
                    }
                }

                // Add driver marker to allMarkers array if it exists
                if (driverMarker) {
                    allMarkers.push(driverMarker);
                }

                // Fit all markers on the map
                if (allMarkers.length > 0) {
                    const group = new L.featureGroup(allMarkers);
                    map.fitBounds(group.getBounds().pad(0.3));
                }
    
                // Driver Marker
                if (data.driver) {
                    const [dLat, dLon] = data.driver;
                    driverLatLng = [dLat, dLon];
                    const driverPopup = userType === "driver" ? "Your location" : "Driver's location";
                    driverMarker = L.marker(driverLatLng, { icon: driverIcon })
                        .addTo(map)
                        .bindPopup(driverPopup)
                        .openPopup();
                }
    
                // Fit both markers in view
                if (driverMarker && passengerMarker) {
                    const group = new L.featureGroup([driverMarker, passengerMarker]);
                    map.fitBounds(group.getBounds().pad(0.3));
                }
    
                // Show modal if driver and passenger are nearby (driver only)
                const rideStatus = document.getElementById("ride-status")?.value;
                journeyStarted = (rideStatus === "ongoing");
                if (data.nearby && userType === "driver" && !journeyStarted && !journeyFinished) {
                    const modal = document.getElementById("startJourneyModal");
                    const closeBtn = document.getElementById("closeModalBtn");
                    const startBtn = document.getElementById("startJourneyBtn");
                    const reminder = document.getElementById("reminder-message");
                
                    if (!modalShown) {
                        console.log("👀 Passenger is nearby. Showing modal...");
                        modal.style.display = "block";
                        modalShown = true;
                    }
                
                    if (closeBtn && !closeBtn.dataset.bound) {
                        closeBtn.dataset.bound = true;
                        closeBtn.addEventListener("click", () => {
                            modal.style.display = "none";
                            if (reminder) {
                                reminder.style.display = "block";
                            }
                        });
                    }
                
                    if (startBtn && !startBtn.dataset.bound) {
                        startBtn.dataset.bound = true;
                        startBtn.addEventListener("click", () => {
                            console.log("Start Journey clicked (modal)");
                            startJourney();
                            modal.style.display = "none";
                        });
                    }
                
                    // Handle reminder click (start journey)
                    if (reminder && !reminder.dataset.bound) {
                        reminder.dataset.bound = true;
                        reminder.addEventListener("click", () => {
                            console.log("Start Journey clicked (reminder)");
                            startJourney();
                            reminder.style.display = "none";
                        });
                    }
                } else {
                    // Hide the reminder if user moves away
                    const reminder = document.getElementById("reminder-message");
                    if (reminder) {
                        reminder.style.display = "none";
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
                    const [passLat, passLon] = data.passenger[currentUsername] || [];
                    const [driverLat, driverLon] = data.driver;
                
                    if (passLat && passLon && driverLat && driverLon) {
                        const distance = getDistanceFromLatLonInMeters(passLat, passLon, driverLat, driverLon);
                        console.log(`Distance to driver: ${Math.round(distance)} meters`);
                
                        if (distance > 250) {
                            console.log("Showing pickup adjust modal based on distance...");
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
                                            iconUrl: "https://cdn-icons-png.flaticon.com/512/854/854878.png",
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
                    }
                }
            })
            .catch(error => console.error("Error fetching live locations:", error));
    }

    // Leaflet map rendering issue
    setTimeout(() => {
        map.invalidateSize();
    }, 500);

    if (userType === "passenger") {
        updateLocation("passenger");
        setTimeout(fetchLiveLocations, 1500); 
    
        setInterval(() => {
            updateLocation("passenger");
            fetchLiveLocations();
        }, 10000);
    
        // Polling for journey status to trigger rating banner
        setInterval(() => {
            fetch('/api/ride_status', {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ride_id: rideId, ride_date: rideDate })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === "done" && !journeyFinished) {
                    journeyFinished = true;
                    document.getElementById("ride-status").value = "done";
                    const banner = document.getElementById("journeyFinishedBanner");
                    const text = document.getElementById("journeyBannerText");
                    text.innerText = "Journey finished. Thank you for riding with Catch My Ride. Please rate your driver.";
    
                    const rateBtn = document.createElement("button");
                    rateBtn.innerText = "Rate Driver";
                    rateBtn.className = "btn btn-light mt-4 rate-btn";
                    rateBtn.style.fontSize = "1.2rem";
                    rateBtn.onclick = function () {
                        showRatingModal(rideId, rideDate);
                    };
    
                    if (!banner.querySelector(".rate-btn")) {
                        banner.appendChild(rateBtn);
                    }
    
                    banner.style.display = "block";
                }
            });
        }, 5000); // check every 5 seconds
    }
     else if (userType === "driver") {
        console.log("Driver detected");
        updateLocation("driver");
        setTimeout(fetchLiveLocations, 1500); // Delay to allow backend to store location
    
        setInterval(() => {
            updateLocation("driver");
            fetchLiveLocations();
        }, 10000);
    }

    // Finish Journey Button Handler
    const finishBtn = document.getElementById("finishJourneyBtn");
    if (finishBtn) {
        finishBtn.addEventListener("click", () => {
            fetch("/api/finish_journey", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ride_id: rideId, ride_date: rideDate })
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById("ride-status").value = "completed";
                journeyFinished = true;
    
                // Show banner instead of reloading
                const banner = document.getElementById("journeyFinishedBanner");
                const text = document.getElementById("journeyBannerText");
                if (userType === "driver") {
                    text.innerText = "Journey finished. Thank you for driving with Catch My Ride.";
                } else {
                    text.innerText = "Journey finished. Thank you for riding with Catch My Ride. Please rate your driver.";
                }
                banner.style.display = "block";
    
                // Optionally hide finish button
                finishBtn.style.display = "none";
            })
            .catch(err => console.error("Error finishing journey:", err));
        });
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

function showRatingModal(rideId, rideDate) {
    const modal = document.getElementById("ratingModal");
    const starContainer = document.getElementById("starContainer");
    const submitBtn = document.getElementById("submitRatingBtn");
    const closeBtn = document.getElementById("closeRatingModal");

    modal.style.display = "block";
    starContainer.innerHTML = "";

    let selectedRating = 0;

    // Create 5 stars
    for (let i = 1; i <= 5; i++) {
        const star = document.createElement("span");
        star.innerHTML = "&#9733;"; // ★
        star.style.fontSize = "2rem";
        star.style.cursor = "pointer";
        star.style.color = "#ccc";
        star.style.margin = "0 5px";

        star.addEventListener("mouseover", () => {
            for (let j = 0; j < i; j++) {
                starContainer.children[j].style.color = "gold";
            }
            for (let j = i; j < 5; j++) {
                starContainer.children[j].style.color = "#ccc";
            }
        });

        star.addEventListener("click", () => {
            selectedRating = i;
        });

        starContainer.appendChild(star);
    }

    // Submit rating
    submitBtn.onclick = () => {
        if (selectedRating === 0) {
            alert("Please select a rating before submitting.");
            return;
        }
    
        fetch("/api/submit_rating", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                ride_id: rideId,
                ride_date: rideDate,
                rating: selectedRating
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(data.error); // Show error message if already rated
                return;
            }
            
            alert(data.message || "Thanks for your rating!");
            modal.style.display = "none";
    
            // Redirect to dashboard
            if (data.redirect_url) {
                window.location.href = data.redirect_url;
            }
        })
        .catch(err => {
            console.error("Error submitting rating:", err);
            alert("Something went wrong. Please try again.");
        });
    };

    // Close modal
    if (closeBtn) {
        closeBtn.onclick = () => {
            modal.style.display = "none";
        };
    }
}