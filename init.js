var exec = require('child_process').exec;

function runPlugin() {
    var pythonScriptPath = __dirname + '/m3utostrm.py';
    
    // Use child process to execute the python file
    exec(`python ${pythonScriptPath} --moviesDirectory=${global.api.configuration.settings.MoviesDirectory} --tvShowsDirectory=${global.api.configuration.settings.TvShowsDirectory} --m3uUrl=${encodeURIComponent(global.api.configuration.settings.M3uUrl)}`, function (error, stdout, stderr) {
        if (error !== null) {
            console.log(`exec error: ${error}`);
        } else {
            console.log('Plugin executed successfully');
        }
    });
}

module.exports = runPlugin;