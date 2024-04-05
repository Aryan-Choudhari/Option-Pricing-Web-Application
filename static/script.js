document.getElementById('optionForm').addEventListener('submit', function(e) {
    e.preventDefault();
    var strike_price = parseFloat(document.getElementById('strike').value);
    var expiry_date = document.getElementById('expiry').value;
    var risk_free_rate = parseFloat(document.getElementById('rate').value);
    var underlying = document.getElementById('underlying').value;

    if (isNaN(risk_free_rate) || isNaN(strike_price)) {
        alert("Please enter valid numbers for Risk-Free Rate and Strike Price.");
        return;
    }

    var today = new Date().toISOString().split('T')[0];
    if (expiry_date <= today) {
        alert("Expiry Date should be a future date.");
        return;
    }

    document.querySelectorAll('.output-box').forEach(function(el) {
        el.innerHTML = '<span class="loading">Loading...</span>';
    });

    fetch('/calculate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            underlying: underlying,
            risk_free_rate: risk_free_rate,
            expiry_date: expiry_date,
            strike_price: strike_price
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok.');
        }
        return response.json();
    })
    .then(data => {
        for (var key in data) {
            var outputElement = document.getElementById(key);
            if (outputElement && data[key] !== null) {
                outputElement.querySelector('.output-box').textContent = data[key].toFixed(2);
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while calculating the option prices. Please try again later.');
    });
});
