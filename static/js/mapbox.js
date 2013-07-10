function get_location() {
    navigator.geolocation.getCurrentPosition(show_map);
}

function show_map(position) {
    var latitude = position.coords.latitude;
    var longitude = position.coords.longitude;
    // let's show a map or do something interesting!
    var map = L.mapbox.map('harita', 'jeffisabelle.map-20zh8hdu')
        .setView([latitude, longitude], 15);


    map.markerLayer.on('click', function(e) {
        map.panTo(e.layer.getLatLng());
    });

    $.get('/complaint/near',
          {'latitude': latitude, 'longitude': longitude},
          function(data) {
              add_markers(map, longitude, latitude, data);
          });

    // console.log(nearcomplaints);
}

function add_markers(map, longitude, latitude, dataarr) {
    var dataobjects = new Array();
    for(var i=0; i<dataarr.length; i++) {
        var dataobject = new Object();
        dataobject.type = "Feature";
        dataobject.geometry = new Object();
        dataobject.geometry.type = "Point";
        dataobject.geometry.coordinates = dataarr[i].location.reverse();
        dataobject.properties = new Object();
        dataobject.properties.title = dataarr[i].title;

        dataobjects.push(dataobject)
    }


    for(var i=0; i<dataobjects.length; i++) {
        console.log(dataobjects[i].properties.title);
        console.log(dataobjects[i].geometry.coordinates);
    }

    var markerLayer = L.mapbox.markerLayer({
        type: "FeatureCollection",
        // features: [{
        //     type: 'Feature',
        //     geometry: {
        //         type: 'Point',
        //         // coordinates here are in longitude, latitude order because
        //         // x, y is the standard for GeoJSON and many formats
        //         coordinates: [longitude, latitude]
        //     },
        //     properties: {
        //         title: 'A Single Marker',
        //         description: 'Just one of me',
        //         // one can customize markers by adding simplestyle properties
        //         // http://mapbox.com/developers/simplestyle/
        //         'marker-size': 'large',
        //         'marker-color': '#f0a'
        //     }
        // }]
        features: dataobjects
    }).addTo(map);
}

get_location();
