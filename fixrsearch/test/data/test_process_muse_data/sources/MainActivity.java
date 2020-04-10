package fixr.plv.colorado.edu.awesomeapp;

import android.os.Bundle;
import android.support.design.widget.FloatingActionButton;
import android.support.design.widget.Snackbar;
import android.support.v7.app.AppCompatActivity;
import android.support.v7.widget.Toolbar;
import android.view.View;
import android.view.Menu;
import android.view.MenuItem;
import android.os.Handler;
import android.os.Message;
import java.util.List;
import android.view.View;
import android.view.ViewGroup;
import android.app.AlertDialog;
import android.app.Dialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;


import java.util.List;

import android.view.View;
import android.view.ViewGroup;

public class MainActivity extends AppCompatActivity {

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    setContentView(R.layout.activity_main);
    Toolbar toolbar = (Toolbar) findViewById(R.id.toolbar);
    setSupportActionBar(toolbar);

    FloatingActionButton fab = (FloatingActionButton) findViewById(R.id.fab);
    fab.setOnClickListener(new View.OnClickListener() {
        @Override
        public void onClick(View view) {
          Snackbar.make(view, "Replace with your own action", Snackbar.LENGTH_LONG)
            .setAction("Action", null).show();
        }
      });
  }

  public void showDialog(Context context) {
    AlertDialog.Builder dialogBuilder = new AlertDialog.Builder(context);

    String title = "Empty Field(s)";
    String message = "Please ensure all fields are contain data";

    dialogBuilder.setMessage(message);

    dialogBuilder.setNegativeButton("OK",
      new DialogInterface.OnClickListener() {
        @Override
        public void onClick(DialogInterface dialog, int which) {

        }
      });
    dialogBuilder.setPositiveButton("Cancel",
      new DialogInterface.OnClickListener() {
        public void onClick(DialogInterface dialog, int which) {
                // continue with delete
        }
      });

    dialogBuilder.create();
    dialogBuilder.show();
  }
}
