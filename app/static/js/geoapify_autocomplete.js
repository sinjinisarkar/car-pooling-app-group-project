// Geoapify Autocomplete 

const apiKey = '8d4289dbcdd4434398807b72a460cca5';

const setupAutocomplete = (inputId) => {
    const input = document.getElementById(inputId);
    const suggestionsContainer = document.createElement('div');
    suggestionsContainer.classList.add('autocomplete-suggestions');
    input.parentNode.appendChild(suggestionsContainer);

    input.addEventListener('input', () => {
        const query = input.value;
        if (query.length > 2) {
            fetch(`https://api.geoapify.com/v1/geocode/autocomplete?text=${encodeURIComponent(query)}&apiKey=${apiKey}`)
                .then(response => response.json())
                .then(data => {
                    suggestionsContainer.innerHTML = '';
                    data.features.forEach(feature => {
                        const suggestion = document.createElement('div');
                        suggestion.classList.add('autocomplete-suggestion');
                        suggestion.textContent = feature.properties.formatted;
                        suggestion.addEventListener('click', () => {
                            input.value = feature.properties.formatted;
                            suggestionsContainer.innerHTML = '';
                        });
                        suggestionsContainer.appendChild(suggestion);
                    });
                });
        } else {
            suggestionsContainer.innerHTML = '';
        }
    });
};

// Initialize Autocomplete for All Relevant Fields
document.addEventListener('DOMContentLoaded', () => {
    const autocompleteFields = [
        'bannerSearchFrom', 'bannerSearchTo',
        'from_location', 'to_location',
        'searchFrom', 'searchTo',
        'newPickup'
    ];

    autocompleteFields.forEach(fieldId => {
        if (document.getElementById(fieldId)) {
            setupAutocomplete(fieldId);
        }
    });
});
