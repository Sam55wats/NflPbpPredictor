const path = require('path');

module.exports = {
  entry: './assets/index.jsx',
  output: {
    path: path.resolve(__dirname, 'static'),
    filename: 'index-bundle.js',
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
        },
      },
      {
        test: /\.css$/i,
        use: ['style-loader', 'css-loader'],
      },
    ]
  },
  resolve: {
    extensions: ['.js', '.jsx'],    
  },

  mode: "development",

};
