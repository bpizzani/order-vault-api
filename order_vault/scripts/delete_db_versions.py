from order_vault.models.db import db
from flask import Blueprint, request, jsonify, session, current_app, redirect, url_for, render_template
from order_vault.main import db

auth_bp = Blueprint("db_version", __name__)

@auth_bp.route("/delete", methods=["GET","POST"])
def delete_db_version():
  # Run raw SQL to delete the broken revision
  db.session.execute("DELETE FROM alembic_version;")
  db.session.commit()
  return "DB Version Deleted"
